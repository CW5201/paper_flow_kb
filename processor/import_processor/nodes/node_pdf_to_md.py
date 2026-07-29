# processor/import_processor/nodes/node_pdf_to_md.py
import json
import logging
import time
import zipfile
from http.client import responses
from pathlib import Path

import requests

from config.mineru_config import mineru_config
from processor.import_processor.base import BaseNode, setup_logging
from processor.import_processor.exceptions import StateFieldError, FileProcessingError, PdfConversionError
from processor.import_processor.state import ImportGraphState


class NodePDFToMD(BaseNode):
    """
    PDF 转 Markdown 节点：PDF结构化解析，调用MinerU云端接口完成文档解析
    """

    name = "node_pdf_to_md"

    def process(self, state: ImportGraphState):
        """节点主处理逻辑"""
        # 1 检查和获取相关路径参数
        pdf_path_obj, output_dir_obj = self._step_1_validate_paths(state)

        # 2 获取上传预签名链接，上传PDF文件并轮询任务，获取zip结果下载链接
        zip_url = self._step_2_upload_and_poll(pdf_path_obj)
        print(f"已经获得下载链接{zip_url}")
        # 3 下载zip压缩包并解压，定位解析生成的md文件路径
        md_path = self._step_3_download_and_extract(zip_url, output_dir_obj, pdf_path_obj.stem)

        # 4 读取markdown文件内容
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
        except Exception:
            print("测试成功")
        # 5 将md路径、文本内容写入state，向下游节点传递数据
        state["md_path"] = md_path
        state["md_content"] = md_content
        return state

    def _step_1_validate_paths(self, state: ImportGraphState):
        """
        步骤1：校验入参，封装Path对象，校验文件与目录是否存在
        :param state: 图流转状态对象
        :return: pdf路径对象,输出目录路径对象
        """
        # 1 从state读取pdf路径参数并校验是否为空
        pdf_path = state.get("pdf_path")
        if not pdf_path:
            raise StateFieldError(field_name="pdf_path", expected_type=str)
        # 读取输出目录参数并校验是否为空
        file_dir = state.get("file_dir")
        if not file_dir:
            raise StateFieldError(field_name="file_dir", expected_type=str)

        # 2 字符串路径封装为Path对象，方便后续文件操作
        pdf_path_obj = Path(pdf_path)
        output_dir_obj = Path(file_dir)

        # 3 校验原始PDF文件、输出目录物理存在
        if not pdf_path_obj.exists():
            raise FileProcessingError(message=f"输入文件不存在{pdf_path}")
        if not output_dir_obj.exists():
            raise FileProcessingError(message=f"目录不存在{output_dir_obj}")
        return pdf_path_obj, output_dir_obj

    def _step_2_upload_and_poll(self, pdf_path_obj):
        """
        步骤2：申请预签名地址上传PDF，循环轮询MinerU解析任务，任务完成返回zip下载链接
        :param pdf_path_obj: PDF文件Path对象
        :return: 解析结果压缩包zip下载链接
        """
        logging.info("_step_2_upload_and_poll上传文件到服务器获得下载链接...")
        # 1 读取配置文件接口凭证与接口地址
        api_token = mineru_config.api_token
        base_url = mineru_config.base_url
        if not api_token:
            raise StateFieldError(message="api_token未配置")
        if not base_url:
            raise StateFieldError(message="api_url未配置")

        # 2 请求批量上传预签名url
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }
        data = {
            "files": [
                {"name": pdf_path_obj.name}
            ],
            "model_version": "vlm"
        }
        url = f"{base_url}/file-urls/batch"
        response = requests.post(url, headers=header, json=data, timeout=30)
        if response.status_code != 200:
            raise FileProcessingError(message=f"文件上传失败:{response.text}")
        result = response.json()
        if result.get("code") != 0:
            raise FileProcessingError(message=f"文件上传失败:{result.get('message')}")
        batch_id = result["data"]["batch_id"]
        signed_url = result["data"]["file_urls"][0]

        # 3 使用put请求将本地PDF上传至预签名地址
        with open(pdf_path_obj, "rb") as pdf_file:
            res_upload = requests.put(signed_url, data=pdf_file, timeout=300)
            if res_upload.status_code != 200:
                raise PdfConversionError(f"文件上传失败，状态码{res_upload.status_code},响应结果:{res_upload.text}")
            self.logger.info(f"文件上传成功")

        # 4 循环轮询解析任务，等待任务完成获取zip下载链接
        poll_url = f"{base_url}/extract-results/batch/{batch_id}"  # 轮询任务结果接口地址
        start_time = time.time()  # 记录任务开始时间，用于超时判断
        timeout_seconds = 600  # 最大轮询超时时间 单位/s
        poll_interval = 3  # 每次轮询间隔时间 单位/s

        while True:
            end_time = time.time() - start_time
            # 判断是否超出最大等待时长，超时抛出异常
            if end_time > timeout_seconds:
                raise FileProcessingError(message="获取下载地址超时")
            try:
                res_poll = requests.get(url=poll_url, timeout=30, headers=header)
            except Exception as e:
                self.logger.error(f"轮询接口异常,{e}")
                time.sleep(poll_interval)
                continue
            if res_poll.status_code != 200:
                raise PdfConversionError(f"HTTP请求失败,状态码{res_poll.status_code},响应内容:{res_poll.text}")
            # 解析轮询返回数据
            poll_data = res_poll.json()
            if poll_data["code"] != 0:
                raise PdfConversionError(f"任务失败,错误信息{poll_data['message']}")
            extract_results = poll_data["data"]["extract_result"]  # 获取批量任务结果数组
            extract_result = extract_results[0]  # 当前文档对应的任务结果
            extract_state = extract_result["state"]  # 获取任务运行状态

            if extract_state == "done":
                full_zip_url = extract_result["full_zip_url"]  # 获取完整压缩包下载链接
                return full_zip_url
            elif extract_state == "failed":
                err_msg = extract_result.get("err_msg", "未知错误")
                raise PdfConversionError(f"任务解析失败batch_id{batch_id},错误信息{err_msg}")
            else:
                # 任务处理中，打印进度日志并休眠等待下一轮轮询
                self.logger.info(f"任务处理中....已耗时{int(end_time)}s状态,{extract_state},batch_id{batch_id}")
                time.sleep(poll_interval)

    def _step_3_download_and_extract(self, zip_url, output_dir_obj, pdf_stem):
        """
        步骤3：远程下载zip压缩包，解压文件，返回md文件完整路径
        :param zip_url: MinerU返回的zip下载地址
        :param output_dir_obj: 文件输出根目录Path对象
        :param pdf_stem: PDF原始文件名（不带后缀）
        :return: 解压后markdown文件绝对路径
        """
        #1下载
        response = requests.get(zip_url)
        if response.status_code != 200:
            raise FileProcessingError(message=f"获取文件失败:{response.text}")
        zip_save_path =output_dir_obj / f"{pdf_stem}.zip"
        with open(zip_save_path,"wb") as f:
            f.write(response.content)

        # 2创建目录
        extract_target_dir = output_dir_obj / pdf_stem
        extract_target_dir.mkdir(parents=True, exist_ok=True)

        #3解压,改名
        with zipfile.ZipFile(zip_save_path,"r") as zip_ref:
            zip_ref.extractall(extract_target_dir)
            # 改名
        target_md_file =extract_target_dir/"full.md"
        new_md_path = target_md_file.with_name(f"{pdf_stem}.md")
        target_md_file.rename(new_md_path)
        self.logger.info(f"重命名成功,文件名:{pdf_stem}.md")

        return str(new_md_path.absolute())

        logging.info("_step_3_download_and_extract下载并解压...")
        # 【待实现逻辑参考】
        # 1. 拼接本地zip临时保存路径
        # zip_temp_path = output_dir_obj / f"{pdf_stem}.zip"
        # 2. 请求下载zip文件保存到本地
        # 3. 创建解压目录，调用zipfile解压
        # 4. 在解压目录匹配 *.md 文件
        # 5. 返回md文件Path字符串

        return "md_path"


if __name__ == '__main__':
    # 初始化日志
    setup_logging()
    # 测试用初始流转状态
    init_state = {
        "pdf_path": r"D:\PantumP3000userguideGDIzh_CNV1.9_1644314230264.pdf",
        "file_dir": r"D:\output"
    }
    # 实例化节点执行转换流程
    node = NodePDFToMD()
    result = node(init_state)
    dumps = json.dumps(result, ensure_ascii=False, indent=4)
    print(dumps)