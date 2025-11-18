### 在容器内开发，环境已经装好
#### 执行以下命令
```shell
docker run --name lanchain-agent -d -v 项目路径:/root/agent --name langchain-agent-dev qingyanjiu/langchain:1.0.3 tail -f /dev/null

docker run --name lanchain-reds -d -p 36379:6379 redis:6-alpine
```

##### 注意：如果容器内要访问redis，可以考虑加network 用服务名来访问
```shell
docker network create langchain-network
docker network connect langchain-network lanchain-agent
docker network connect langchain-network lanchain-redis
```