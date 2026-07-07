import os

from dotenv import load_dotenv
load_dotenv(override=True)

from langchain_openai import ChatOpenAI

# ---- 阿里云百炼 (DashScope) - OpenAI 兼容模式 -------------------------------
# 使用前请在系统环境变量或 .env 文件中设置 DASHSCOPE_API_KEY
# 可在阿里云百炼控制台获取: https://bailian.console.aliyun.com/?apiKey=1
model = ChatOpenAI(
    model="qwen-plus",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


# ---- Anthropic ------------------------------------------------------------
# from langchain.chat_models import init_chat_model
# model = init_chat_model("anthropic:claude-haiku-4-5")



# ---- Azure OpenAI ---------------------------------------------------------
# from langchain_openai import AzureChatOpenAI
# from azure.identity import InteractiveBrowserCredential

# credential = InteractiveBrowserCredential()


# def get_token():
#     token = credential.get_token("https://cognitiveservices.azure.com/.default")
#     return token.token

# Make sure AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are set.

# Azure OpenAI: Using environment variables
# model = AzureChatOpenAI(
#     azure_deployment="gpt-4o",
#     streaming=True,
# )

# Azure OpenAI: Using Azure AD
# model = AzureChatOpenAI(
#     api_version="2024-03-01-preview",
#     azure_endpoint="https://deployment.openai.azure.com/",
#     azure_deployment="gpt-4o",
#     azure_ad_token_provider=get_token,
# )


# ---- AWS Bedrock ----------------------------------------------------------
# import os
# from langchain_aws import ChatBedrockConverse

# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")
# AWS_MODEL_ARN = os.getenv("AWS_MODEL_ARN")

# model = ChatBedrockConverse(
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION_NAME,
#     provider="anthropic",
#     model_id=AWS_MODEL_ARN,
# )


# ---- Google Vertex AI -----------------------------------------------------
# Make sure your Vertex AI credentials are set up and GOOGLE_APPLICATION_CREDENTIALS
# points to the JSON file.

# import os
# from pathlib import Path
# from langchain.chat_models import init_chat_model

# # Resolve project root and load .env (utils/ -> project root is one level up)
# project_root = Path(__file__).resolve().parent.parent
# load_dotenv(dotenv_path=project_root / ".env", override=True)

# # Make the credentials path absolute if it was given as a relative path
# if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
#     cred_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
#     if not os.path.isabs(cred_path):
#         os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(project_root / cred_path.lstrip("./"))

# model = init_chat_model("google_vertexai:gemini-2.5-flash")