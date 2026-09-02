sandbox/ 是安全沙箱的工作区（容器内路径 /workspace）。

文件工具：只能读写这个目录。
execute_python / execute_shell / git_*：在 Docker 容器里跑。
  能出网，但不进 Postgres/Redis 那张网；只读根文件系统、非 root、有内存和进程数上限。
  看不到项目源码、.env、宿主机 Python。

先启动：docker compose up -d --build
