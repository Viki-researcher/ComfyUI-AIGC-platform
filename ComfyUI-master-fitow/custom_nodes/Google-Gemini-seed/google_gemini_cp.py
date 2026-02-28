
# ============================================================================
# ComfyUI Gemini Native Node (147AI 定制版)
# API 地址固定为 https://nn.147ai.com
# 支持分辨率 (1K/2K/4K) 和宽高比配置
# ============================================================================

import torch
from PIL import Image
from io import BytesIO
import base64
import comfy.utils

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


class ComfyUI_Gemini_Native:
    """
    Nano Banana Pro - Gemini 图片生成节点 (147ai.com)
    API 地址固定为 https://nn.147ai.com
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
            },
            "optional": {
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
    RETURN_NAMES = ("image", "response")
    FUNCTION = "generate_image"
    CATEGORY = "147ai.com"
    
    def generate_image(self, prompt, api_key, model, mode, aspect_ratio, image_size,
                       image1=None, image2=None, image3=None, image4=None,
                       image5=None, image6=None, image7=None, image8=None):
        
        if not api_key.strip():
            error_msg = "❌ API key is required"
            print(error_msg)
            blank_image = Image.new('RGB', (1024, 1024), color='white')
            return (pil2tensor(blank_image), error_msg)
        
        try:
            from google import genai
            # import google.genai as genai
            from google.genai import types
            
            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(10)
            
            # 创建客户端 - 使用固定的 API 地址
            http_options = types.HttpOptions(base_url=FIXED_BASE_URL)
            client = genai.Client(api_key=api_key, http_options=http_options)
            
            pbar.update_absolute(20)
            
            # 构建请求内容
            contents = []
            
            # 处理 img2img 模式的输入图片
            if mode == "img2img":
                all_images = [image1, image2, image3, image4, image5, image6, image7, image8]
                
                image_count = 0
                for img_tensor in all_images:
                    if img_tensor is not None:
                        pil_img = tensor2pil(img_tensor)[0]
                        if pil_img:
                            img_bytes = BytesIO()
                            pil_img.save(img_bytes, format="PNG")
                            img_bytes.seek(0)
                            
                            image_part = types.Part.from_bytes(
                                data=img_bytes.read(),
                                mime_type="image/png"
                            )
                            contents.append(image_part)
                            image_count += 1
                
                print(f"📷 Processing {image_count} input images")
            
            # 添加文本提示
            contents.append(prompt)
            
            pbar.update_absolute(30)
            
            # 配置图片生成参数 - 使用 ImageConfig 支持 aspect_ratio 和 image_size
            if aspect_ratio == "Auto":
                image_config = types.ImageConfig(
                    image_size=image_size,  # 1K, 2K, 4K
                )
            else:
                image_config = types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,  # 1K, 2K, 4K
                )
            
            config = types.GenerateContentConfig(
                response_modalities=['IMAGE', 'TEXT'],
                image_config=image_config,
            )
            
            print(f"🚀 Calling Gemini API: {model}")
            print(f"   Base URL: {FIXED_BASE_URL}")
            print(f"   Aspect Ratio: {aspect_ratio}")
            print(f"   Image Size: {image_size}")
            
            pbar.update_absolute(40)
            
            # 调用 API
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            pbar.update_absolute(80)
            
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
                                print(f"✅ Image generated: {pil_image.size}")
                            elif hasattr(part, 'text') and part.text:
                                response_text += part.text + "\n"
            
            pbar.update_absolute(100)
            
            if generated_images:
                combined_tensor = torch.cat(generated_images, dim=0)
                info = f"✅ Generated {len(generated_images)} image(s)\n"
                info += f"Model: {model}\n"
                info += f"Aspect Ratio: {aspect_ratio}\n"
                info += f"Image Size: {image_size}\n"
                if response_text:
                    info += f"\nResponse:\n{response_text}"
                return (combined_tensor, info)
            else:
                error_msg = f"❌ No image generated\nResponse: {response_text or 'Empty response'}"
                print(error_msg)
                blank_image = Image.new('RGB', (1024, 1024), color='white')
                return (pil2tensor(blank_image), error_msg)
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            blank_image = Image.new('RGB', (1024, 1024), color='white')
            return (pil2tensor(blank_image), error_msg)


NODE_CLASS_MAPPINGS = {
    "ComfyUI_Gemini_Native": ComfyUI_Gemini_Native,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComfyUI_Gemini_Native": "Nano Banana Pro (147ai.com)",
}
