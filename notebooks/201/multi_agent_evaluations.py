from langsmith import Client
client = Client()

examples = [
    {
        "question": "我叫 Aaron Mitchell。账户 ID 是 32。我账户关联的电话号码是 +1 (204) 452-6452。我想查一下我最近一次歌曲购买的发票编号，你能帮我查一下吗？",
        "response": "您最近一次购买的发票编号（Invoice ID）是 342。",
    },
    {
        "question": "我想要退款。",
        "response": "我无法直接处理退款。关于此问题，请直接联系客户支持。",
    },
    {
        "question": "Wish You Were Here 是谁录制的来着？",
        "response": "Wish You Were Here 是 Pink Floyd 的一张专辑。",
    },
    {
        "question": "你们有哪些 Coldplay 的专辑？",
        "response": "目前我们的目录中没有 Coldplay 的专辑。",
    },
    {
        "question": "我怎样才能成为亿万富翁？",
        "response": "我在这里只能帮您解答与我们数字音乐商店相关的问题。如果您对我们的音乐目录或历史购买有任何疑问，欢迎随时咨询！",
    },
]
