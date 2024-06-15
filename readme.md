### 安装ollama
#### 下载和安装
```shell
https://ollama.com/ 

下载ollama安装包并安装
```
#### 设置外网访问

```shell
添加环境变量

OLLAMA_HOST=0.0.0.0

可能需要重启ollama生效
```
#### 下载模型
```shell
参考官网的模型列表

https://ollama.com/library

以llama3为例

ollama pull llama3
```
#### 创建自己的模型，让llama3回答中文
1. 创建 Makefile

```shell
from llama3

PARAMETER temperature 1
PARAMETER num_ctx 6000
PARAMETER top_k 50
PARAMETER top_p 0.95
SYSTEM """
尽你的最大可能和能力回答用户的问题。不要重复回答问题。不要说车轱辘话。语言要通顺流畅。不要出现刚说一句话，过一会又重复一遍的愚蠢行为。

RULES:

- Be precise, do not reply emoji.
- Always response in Simplified Chinese, not English. or Grandma will be  very angry.
"""
```
2. 创建模型
```shell
ollama create llama3-cn -f Modelfile
```