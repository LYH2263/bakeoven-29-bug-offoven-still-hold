# BakeOven

烘焙占炉排程：发酵+烘烤半开区间占用炉位，冲突检测与下一可开工窗口。

## 离炉醒发

产品页可勾选「醒发不占炉」：勾选后发酵分钟不产生占炉段，仅烘烤段占炉，但烘烤起点仍不得早于开工分钟 + 发酵分钟；可开工窗口只按烘烤分钟找空档，甘特只画烘烤条，批次页仍列发酵止与烘烤止以便核对。取消勾选后，新排入的批次恢复发酵+烘烤两段占炉。发酵 0 分钟的产品（如布朗尼）始终只有烘烤段。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4500 |
| API | http://localhost:9500 |
| API 文档 | http://localhost:9500/docs |
| Postgres | localhost:5446 |

健康检查：`GET http://localhost:9500/api/health`

## 页面

- `/products` — 产品
- `/ovens` — 炉位
- `/batches` — 批次
- `/gantt` — 甘特
- `/conflicts` — 冲突
- `/windows` — 可开工

## 使用说明

1. 查看产品配方时长与炉位。
2. 创建生产批次，系统按半开区间占炉并检测冲突。
3. 甘特查看占用；冲突与可开工窗口辅助排产。

## 开发与测试

```bash
docker compose exec api pytest -q
```
