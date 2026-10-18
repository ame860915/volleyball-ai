from pathlib import Path
from ultralytics import YOLO

if __name__ == "__main__":
    model_path = Path(
        r"D:\2026\4.Professional\Volleyball\YoloV11_TrainMySelf"
        r"\runs\detect\volleyball_runs\exp1-4\weights\best.pt"
    )

    video_path = Path(
        r"D:\2026\4.Professional\Volleyball\Data\Video\20260719.mp4"
    )

    # 執行前先確認路徑
    if not model_path.is_file():
        raise FileNotFoundError(f"找不到模型：{model_path}")

    if not video_path.is_file():
        raise FileNotFoundError(f"找不到影片：{video_path}")

    print(f"模型：{model_path}")
    print(f"影片：{video_path}")

    model = YOLO(str(model_path))

    model.predict(
        source=str(video_path),
        save=True,          # 儲存標註後的影片
        conf=0.25,          # 抓不到球可降至 0.15
        imgsz=640,          # 與訓練設定一致
        show=False,         # True：顯示即時預測視窗
        project=r"D:\2026\4.Professional\Volleyball\YoloV11_TrainMySelf\volleyball_preds",
        name="video1"
    )