sandbox/ 是 V1 工具的工作区。

list_dir / read_file / write_file / delete_file
execute_python / execute_shell
git_*

都不能读到这个目录外面。这不是安全沙箱，只是防止 Agent 随手改项目源码。
