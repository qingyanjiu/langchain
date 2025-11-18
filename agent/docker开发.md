### 在容器内开发，环境已经装好
#### 执行以下命令
```shell
docker run -d -v 项目路径:/root/agent --name langchain-agent-dev qingyanjiu/langchain:1.0.3 tail -f /dev/null
```