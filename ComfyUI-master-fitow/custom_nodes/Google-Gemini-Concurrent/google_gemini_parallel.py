# ============================================================================
# ComfyUI Gemini Parallel Node (147AI 定制版)
# 支持单张输入图像，并发生成多张图像
# API 地址固定为 https://nn.147ai.com
# ============================================================================

import torch
from PIL import Image
from io import BytesIO
import base64
import comfy.utils
import concurrent.futures
import threading
from typing import List, Tuple, Optional

# 固定的 API 地址
FIXED_BASE_URL = "https://147ai.com"

def pil2tensor(image):
    import numpy as np
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def tensor2pil(tensor):
    import numpy as np
    if tensor.dim() == 4:
        tensor = tensor.squeeze(0)
    image = Image.fromarray((tensor.numpy() * 255).astype(np.uint8))
    return [image]

class ComfyUI_Gemini_Parallel:
    """
    Nano Banana Pro - Gemini 并发生成节点 (147ai.com)
    单张输入图像，并发生成多张图像
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
                    "gemini-2.5-flash-image-preview"
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
                "input_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "responses")
    FUNCTION = "generate_parallel"
    CATEGORY = "147ai.com"

    def _generate_single_image(self, task_data: dict) -> Tuple[Optional[torch.Tensor], str]:
        """生成单个图像的任务"""
        try:
            from google import genai
            from google.genai import types

            prompt = task_data["prompt"]
            api_key = task_data["api_key"]
            model = task_data["model"]
            mode = task_data["mode"]
            aspect_ratio = task_data["aspect_ratio"]
            image_size = task_data["image_size"]
            seed = task_data["seed"]
            input_image = task_data["input_image"]
            task_id = task_data["task_id"]

            # 创建客户端
            http_options = types.HttpOptions(base_url=FIXED_BASE_URL)
            client = genai.Client(api_key=api_key, http_options=http_options)

            # 构建请求内容
            contents = []

            # 处理输入图片（如果是 img2img 模式）
            if mode == "img2img" and input_image is not None:
                pil_img = tensor2pil(input_image)[0]
                if pil_img:
                    img_bytes = BytesIO()
                    pil_img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)

                    image_part = types.Part.from_bytes(
                        data=img_bytes.read(),
                        mime_type="image/png"
                    )
                    contents.append(image_part)

            # 添加文本提示
            contents.append(f"{prompt} (生成 #{task_id})")

            # 配置图片生成参数
            if aspect_ratio == "Auto":
                image_config = types.ImageConfig(
                    image_size=image_size,
                )
            else:
                image_config = types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )

            config_kwargs = {
                "response_modalities": ['IMAGE', 'TEXT'],
                "image_config": image_config,
            }

            # 只有当 seed >= 0 时才设置 seed
            if seed is not None and seed >= 0:
                config_kwargs["seed"] = seed + task_id  # 每个任务使用不同的 seed

            config = types.GenerateContentConfig(**config_kwargs)

            # 调用 API
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

            # 解析响应
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
                return (combined_tensor, success_msg)
            else:
                error_msg = f"❌ Task #{task_id}: No image generated\nResponse: {response_text or 'Empty response'}"
                return (None, error_msg)

        except Exception as e:
            error_msg = f"❌ Task #{task_data['task_id']} Error: {str(e)}"
            return (None, error_msg)

    def generate_parallel(self, prompt, api_key, model, mode, aspect_ratio,
                         image_size, generation_count, seed=-1, input_image=None):

        if not api_key.strip():
            error_msg = "❌ API key is required"
            print(error_msg)
            blank_image = Image.new('RGB', (1024, 1024), color='white')
            return (pil2tensor(blank_image), error_msg)

        try:
            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(5)

            print(f"🔄 Starting parallel generation: {generation_count} images from 1 input")

            # 准备并发任务
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
                    "input_image": input_image,
                    "task_id": i + 1
                }
                tasks.append(task_data)

            pbar.update_absolute(15)

            # 使用线程池并发执行
            results = []
            successful_results = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(generation_count, 5)) as executor:
                # 提交所有任务
                future_to_task = {executor.submit(self._generate_single_image, task): task for task in tasks}

                # 收集结果
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
                        print(f'❌ Task #{task_id} generated an exception: {exc}')
                        results.append((None, f"❌ Task #{task_id} failed: {str(exc)}"))

                    completed_count += 1
                    progress = 15 + int((completed_count / len(tasks)) * 80)
                    pbar.update_absolute(progress)

            pbar.update_absolute(95)

            # 合并所有成功生成的图像
            if successful_results:
                final_tensor = torch.cat(successful_results, dim=0)

                # 构建响应信息
                response_info = f"🎉 Parallel generation completed!\n"
                response_info += f"Input image: {'Yes' if input_image is not None else 'No'}\n"
                response_info += f"Total tasks: {generation_count}\n"
                response_info += f"Successful: {len(successful_results)}\n"
                response_info += f"Failed: {generation_count - len(successful_results)}\n\n"

                # 按任务顺序显示结果
                sorted_results = sorted(results, key=lambda x: int(x[1].split('#')[1].split(':')[0]) if 'Task #' in x[1] else 999)
                for result in sorted_results:
                    response_info += f"{result[1]}\n\n"

                pbar.update_absolute(100)
                return (final_tensor, response_info.strip())
            else:
                error_msg = "❌ All parallel tasks failed\n"
                for result in results:
                    error_msg += f"{result[1]}\n"
                print(error_msg)
                blank_image = Image.new('RGB', (1024, 1024), color='white')
                pbar.update_absolute(100)
                return (pil2tensor(blank_image), error_msg)

        except Exception as e:
            error_msg = f"❌ Parallel processing error: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            blank_image = Image.new('RGB', (1024, 1024), color='white')
            return (pil2tensor(blank_image), error_msg)


NODE_CLASS_MAPPINGS = {
    "ComfyUI_Gemini_Parallel": ComfyUI_Gemini_Parallel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComfyUI_Gemini_Parallel": "Nano Banana Pro Parallel (147ai.com)",
}