# Kiến trúc hiện tại (SmartPark), ảnh chụp 01/09/2026

Trạng thái thật, suy từ code + deploy podman đang chạy. Đánh dấu: DEPLOYED (đang chạy podman Mac), GAP (đã code nhưng chưa chạy được), PI (thuộc Raspberry Pi, chưa deploy).

## Deployment + luồng dữ liệu

```mermaid
graph TB
    subgraph HOST["Host Mac (máy dev)"]
        BR["Trình duyệt · React SPA<br/>getUserMedia dùng WEBCAM MÁY<br/>gate / sessions / config / stats"]
    end

    subgraph POD["Podman · libkrun VM (arm64)"]
        FE["frontend · nginx :5173→80<br/>DEPLOYED"]
        BE["backend · FastAPI :8000<br/>routers: auth, captures, sessions, readings,<br/>payments, config, vehicle_groups, stats, gate_ws...<br/>DEPLOYED"]
        RET["retention worker<br/>xóa dữ liệu biển hết hạn (luật DLCN)<br/>DEPLOYED"]
        DB[("postgres :5432 · pgdata<br/>session, plate_reading, payment,<br/>vehicle_group, price_rule, user, audit_log...<br/>DEPLOYED · data còn nguyên")]
        VOL[["images volume"]]
    end

    subgraph PI["Raspberry Pi 5 · Linux native (PI · tuần 8, chưa deploy)"]
        EDGE["edge worker<br/>camera /dev/video0 + trigger GPIO<br/>chạy ML tại chỗ"]
    end

    MLP["src/ml · OnnxAlprPipeline<br/>YOLO .pt + OCR CRNN .onnx + style .onnx<br/>(thư viện, chạy IN-PROCESS)"]

    BR -->|"1· tải SPA"| FE
    BR -->|"2· POST /captures/infer (JPEG từ webcam)"| BE
    BR <-->|"WS /gate_ws realtime"| BE
    BE -->|"đọc/ghi"| DB
    BE -->|"ảnh"| VOL
    RET -->|"quét + xóa"| DB
    BE -. "INFERENCE_ENGINE=ml<br/>GAP: image backend thiếu torch + src/ml → /captures/infer 500" .-> MLP
    EDGE -->|"POST /captures (payload đã suy luận, X-Edge-Key)"| BE
    EDGE ==>|"nạp in-process"| MLP

    classDef deployed fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef gap fill:#fef9c3,stroke:#ca8a04,color:#713f12;
    classDef pi fill:#e0e7ff,stroke:#4f46e5,color:#312e81;
    class FE,BE,RET,DB,VOL deployed;
    class MLP gap;
    class EDGE pi;
```

## Hai đường nạp ảnh (cùng đổ về backend)

- **Đường A · Kiosk/trình duyệt (đang xây, chạy được trên Mac):** webcam do TRÌNH DUYỆT truy cập (host), chụp JPEG, `POST /captures/infer`. Backend tự chạy ML (`INFERENCE_ENGINE=ml`) rồi ra quyết định VÀO/RA. Container KHÔNG cần camera.
- **Đường B · Edge/Pi (thuộc Pi):** edge worker có camera + trigger riêng, chạy ML tại chỗ, `POST /captures` kèm payload đã suy luận (xác thực `X-Edge-Key`). Backend không suy luận lại.

Cả hai dùng chung `src/ml` (OnnxAlprPipeline) và chung schema payload. ML là thư viện nạp in-process, không phải service riêng.

## Gap chặn đường A ngay lúc này

`INFERENCE_ENGINE=ml` đã bật, nhưng image backend build từ context `./src/backend`, chỉ cài `requirements.txt`. Hệ quả:
- không có `ultralytics/onnxruntime/torch` trong image,
- không có `src/ml` (code + weights) trong image,
- `POST /captures/infer` trả **500**.

Để chạy đường A trong podman: build ml-backend image (context repo root, COPY `src/ml`, cài thêm `requirements-ml.txt`). Cùng image chạy được trên Pi single-box.
```
