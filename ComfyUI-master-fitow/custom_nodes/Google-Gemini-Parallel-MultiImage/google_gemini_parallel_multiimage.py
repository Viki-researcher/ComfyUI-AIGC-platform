# ============================================================================
# ComfyUI Gemini Parallel Multi-Image Node (147AI 定制版)
# 支持多张输入图像 + 并发生成多张图像
# 基于 Google-Gemini-Concurrent 增加 image1~image8 多图输入
# API 地址固定为 https://147ai.com
# ============================================================================

import torch
from PIL import Image
from io import BytesIO
import comfy.utils
import concurrent.futures
from typing import List, Tuple, Optional

FIXED_BASE_URL = "https://147ai.com"
LOG_PREFIX = "[Gemini-MultiImage]"


def _log(step: str, msg: str = ""):
    """统一格式的步骤日志"""
    line = f"{LOG_PREFIX} [{step}] {msg}".strip()
    print(line)


def pil2tensor(image):
    import numpy as np
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def tensor2pil(tensor):
    import numpy as np
    if tensor.dim() == 4:
        tensor = tensor.squeeze(0)
    image = Image.fromarray((tensor.numpy() * 255).astype(np.uint8))
    return [image]


def collect_image_parts(all_images: list) -> list:
    """
    从 image1~image8 等张量列表中收集非空的 PIL，并转为 API 所需的 Part 列表。
    返回 list of types.Part（调用方需 from google.genai import types）。
    """
    from google.genai import types
    _log("collect_image_parts", "开始收集输入图像...")
    parts = []
    for img_tensor in all_images:
        if img_tensor is not None:
            pil_img = tensor2pil(img_tensor)[0]
            if pil_img:
                img_bytes = BytesIO()
                pil_img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                parts.append(
                    types.Part.from_bytes(
                        data=img_bytes.read(),
                        mime_type="image/png"
                    )
                )
    _log("collect_image_parts", f"收集完成，共 {len(parts)} 张图像")
    return parts


class ComfyUI_Gemini_Parallel_MultiImage:
    """
    Nano Banana Pro - Gemini 并发生成节点（多图输入版）
    支持 image1~image8 多图输入，并发生成多张图像
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "model": ([
                    "gemini-3-pro-image-preview",
                    "gemini-3-pro-image-preview-stable",
                    "gemini-2.5-flash-image",
                    "gemini-2.5-flash-image-preview",
                    "gemini-3.1-flash-image-preview"
                ], {"default": "gemini-3-pro-image-preview"}),
                "mode": (["text2img", "img2img"], {"default": "text2img"}),
                "aspect_ratio": ([
                    "Auto", "1:1", "16:9", "9:16", "4:3", "3:4",
                    "3:2", "2:3", "21:9", "4:5", "5:4"
                ], {"default": "Auto"}),
                "image_size": (["1K", "2K", "4K"], {"default": "1K"}),
                "generation_count": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
            },
            "optional": {
                "seed": ("INT", {"default": -1}),
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "image6": ("IMAGE",),
                "image7": ("IMAGE",),
                "image8": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "responses")
    FUNCTION = "generate_parallel"
    CATEGORY = "147ai.com"

    def _generate_single_image(self, task_data: dict) -> Tuple[Optional[torch.Tensor], str]:
        """生成单个图像的任务（支持多图作为输入）"""
        task_id = task_data["task_id"]
        try:
            _log("single_task", f"Task #{task_id} 开始")
            from google import genai
            from google.genai import types

            prompt = task_data["prompt"]
            api_key = task_data["api_key"]
            model = task_data["model"]
            mode = task_data["mode"]
            aspect_ratio = task_data["aspect_ratio"]
            image_size = task_data["image_size"]
            seed = task_data["seed"]
            all_images = task_data["all_images"]

            _log("single_task", f"Task #{task_id} 创建客户端 (model={model}, mode={mode})")
            http_options = types.HttpOptions(base_url=FIXED_BASE_URL)
            client = genai.Client(api_key=api_key, http_options=http_options)

            contents = []

            # 多图输入：img2img 时将所有提供的 image1~image8 加入 contents
            if mode == "img2img" and all_images:
                image_parts = collect_image_parts(all_images)
                contents.extend(image_parts)

            contents.append(f"{prompt} (生成 #{task_id})")
            _log("single_task", f"Task #{task_id} 构建 contents 完成 (含 {len(contents)} 项)")

            if aspect_ratio == "Auto":
                image_config = types.ImageConfig(image_size=image_size)
            else:
                image_config = types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )

            config_kwargs = {
                "response_modalities": ['IMAGE', 'TEXT'],
                "image_config": image_config,
            }
            if seed is not None and seed >= 0:
                config_kwargs["seed"] = seed + task_id

            config = types.GenerateContentConfig(**config_kwargs)
            _log("single_task", f"Task #{task_id} 调用 API generate_content...")
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            _log("single_task", f"Task #{task_id} API 返回，解析响应...")

            response_text = ""
            generated_images = []

            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                img_data = part.inline_data.data
                                pil_image = Image.open(BytesIO(img_data))
                                tensor_image = pil2tensor(pil_image)
                                generated_images.append(tensor_image)
                            elif hasattr(part, 'text') and part.text:
                                response_text += part.text + "\n"

            if generated_images:
                combined_tensor = torch.cat(generated_images, dim=0)
                success_msg = f"✅ Task #{task_id}: Generated {len(generated_images)} image(s)"
                if response_text.strip():
                    success_msg += f"\nResponse: {response_text.strip()}"
                _log("single_task", f"Task #{task_id} 完成，生成 {len(generated_images)} 张图")
                return (combined_tensor, success_msg)
            else:
                error_msg = f"❌ Task #{task_id}: No image generated\nResponse: {response_text or 'Empty response'}"
                _log("single_task", f"Task #{task_id} 未生成图像")
                return (None, error_msg)

        except Exception as e:
            error_msg = f"❌ Task #{task_data['task_id']} Error: {str(e)}"
            _log("single_task", f"Task #{task_id} 异常: {str(e)}")
            return (None, error_msg)

    def generate_parallel(self, prompt, api_key, model, mode, aspect_ratio,
                          image_size, generation_count, seed=-1,
                          image1=None, image2=None, image3=None, image4=None,
                          image5=None, image6=None, image7=None, image8=None):

        _log("step_1", "节点开始执行：参数校验")
        if not api_key.strip():
            error_msg = "❌ API key is required"
            _log("step_1", error_msg)
            print(error_msg)
            blank_image = Image.new('RGB', (1024, 1024), color='white')
            return (pil2tensor(blank_image), error_msg)

        try:
            _log("step_2", "收集输入图像 (image1~image8)")
            all_images = [image1, image2, image3, image4, image5, image6, image7, image8]
            image_count = sum(1 for x in all_images if x is not None)
            _log("step_2", f"有效输入图像数: {image_count}")

            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(5)

            _log("step_3", f"构建 {generation_count} 个并发生成任务 (mode={mode}, model={model})")
            print(f"🔄 Parallel multi-image: {generation_count} generations, {image_count} input image(s)")

            tasks = []
            for i in range(generation_count):
                task_data = {
                    "prompt": prompt,
                    "api_key": api_key,
                    "model": model,
                    "mode": mode,
                    "aspect_ratio": aspect_ratio,
                    "image_size": image_size,
                    "seed": seed,
                    "all_images": all_images,
                    "task_id": i + 1
                }
                tasks.append(task_data)
            _log("step_3", f"任务列表已构建，共 {len(tasks)} 个任务")

            pbar.update_absolute(15)

            results = []
            successful_results = []
            _log("step_4", f"提交并发执行 (max_workers={min(generation_count, 5)})")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(generation_count, 5)) as executor:
                future_to_task = {executor.submit(self._generate_single_image, t): t for t in tasks}
                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)
                        if result[0] is not None:
                            successful_results.append(result[0])
                    except Exception as exc:
                        task_id = task["task_id"]
                        _log("step_4", f"Task #{task_id} 异常: {exc}")
                        print(f'❌ Task #{task_id} generated an exception: {exc}')
                        results.append((None, f"❌ Task #{task_id} failed: {str(exc)}"))
                    completed_count += 1
                    _log("step_4", f"已完成 {completed_count}/{len(tasks)} 个任务")
                    progress = 15 + int((completed_count / len(tasks)) * 80)
                    pbar.update_absolute(progress)

            pbar.update_absolute(95)
            _log("step_5", f"所有任务执行完毕，成功 {len(successful_results)}，失败 {len(tasks) - len(successful_results)}")

            if successful_results:
                final_tensor = torch.cat(successful_results, dim=0)
                response_info = "🎉 Parallel multi-image generation completed!\n"
                response_info += f"Input images: {image_count}\n"
                response_info += f"Total tasks: {generation_count}\n"
                response_info += f"Successful: {len(successful_results)}\n"
                response_info += f"Failed: {generation_count - len(successful_results)}\n\n"
                sorted_results = sorted(
                    results,
                    key=lambda x: int(x[1].split('#')[1].split(':')[0]) if 'Task #' in x[1] else 999
                )
                for result in sorted_results:
                    response_info += f"{result[1]}\n\n"
                _log("step_6", "汇总结果并返回图像与响应文本")
                pbar.update_absolute(100)
                return (final_tensor, response_info.strip())
            else:
                _log("step_6", "无成功结果，返回错误信息")
                error_msg = "❌ All parallel tasks failed\n"
                for result in results:
                    error_msg += f"{result[1]}\n"
                print(error_msg)
                blank_image = Image.new('RGB', (1024, 1024), color='white')
                pbar.update_absolute(100)
                return (pil2tensor(blank_image), error_msg)

        except Exception as e:
            _log("error", f"节点异常: {str(e)}")
            error_msg = f"❌ Parallel processing error: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            blank_image = Image.new('RGB', (1024, 1024), color='white')
            return (pil2tensor(blank_image), error_msg)


NODE_CLASS_MAPPINGS = {
    "ComfyUI_Gemini_Parallel_MultiImage": ComfyUI_Gemini_Parallel_MultiImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComfyUI_Gemini_Parallel_MultiImage": "Nano Banana Pro Parallel Multi-Image (147ai.com)",
}
