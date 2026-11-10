计时试跑，非正式结果。发现Popen.wait(timeout)以轮询等待，短查询墙钟可能额外计入轮询等待尾延迟；已停止自己的worker且不复用这些数据。正式comparison-five改为阻塞waitpid，独立Timer负责超时kill。全部80次从头重测，无变更A/B二进制或输入。
