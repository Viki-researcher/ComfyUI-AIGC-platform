from tortoise import fields

from .base import BaseModel, TimestampMixin


class ChatSession(BaseModel, TimestampMixin):
    user_id = fields.BigIntField(description="用户ID", index=True)
    title = fields.CharField(max_length=200, default="新对话", description="会话标题")
    model_provider = fields.CharField(max_length=50, default="", description="模型提供商")
    model_name = fields.CharField(max_length=100, default="", description="模型名称")
    system_prompt = fields.TextField(default="", description="系统提示词")
    is_deleted = fields.BooleanField(default=False, description="软删除", index=True)

    class Meta:
        table = "chat_sessions"
        ordering = ["-updated_at"]


class ChatMessage(BaseModel, TimestampMixin):
    session_id = fields.BigIntField(description="会话ID", index=True)
    role = fields.CharField(max_length=20, description="角色(user/assistant/system)")
    content = fields.TextField(description="消息内容")
    token_count = fields.IntField(default=0, description="Token数量")

    class Meta:
        table = "chat_messages"
        ordering = ["created_at"]


class ChatDocument(BaseModel, TimestampMixin):
    user_id = fields.BigIntField(description="用户ID", index=True)
    filename = fields.CharField(max_length=500, description="原始文件名")
    file_path = fields.CharField(max_length=1000, description="存储路径")
    file_size = fields.IntField(default=0, description="文件大小(字节)")
    file_type = fields.CharField(max_length=50, description="文件类型")
    chunk_count = fields.IntField(default=0, description="分块数量")
    status = fields.CharField(max_length=20, default="processing", description="状态(processing/ready/error)")
    error_msg = fields.TextField(default="", description="错误信息")

    class Meta:
        table = "chat_documents"
        ordering = ["-created_at"]


class DocumentChunk(BaseModel, TimestampMixin):
    document_id = fields.BigIntField(description="文档ID", index=True)
    content = fields.TextField(description="分块文本内容")
    chunk_index = fields.IntField(description="分块索引")
    embedding = fields.TextField(default="", description="嵌入向量(JSON)")

    class Meta:
        table = "document_chunks"
        ordering = ["chunk_index"]


class TokenUsage(BaseModel, TimestampMixin):
    user_id = fields.BigIntField(description="用户ID", index=True)
    provider = fields.CharField(max_length=50, default="", description="模型提供商", index=True)
    model = fields.CharField(max_length=100, default="", description="模型名称", index=True)
    prompt_tokens = fields.IntField(default=0, description="Prompt Token 数量")
    completion_tokens = fields.IntField(default=0, description="Completion Token 数量")

    class Meta:
        table = "token_usage"
        ordering = ["-created_at"]
