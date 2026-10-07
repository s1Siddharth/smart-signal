from ultralytics import YOLO

def train_model():
    # Load the base model (you can change this to yolov8s.pt if you want the small model)
    model = YOLO("yolov8n.pt")
    
    # Train the model using the dataset configuration
    # Adjust epochs and imgsz depending on your hardware
    # Since it's a small dataset (22 images), we don't need many epochs.
    results = model.train(
        data=r"a:\OE\dataset\data.yaml",
        epochs=50,
        imgsz=640,
        batch=4,
        name="custom_yolov8n_finetune"
    )
    
    print("\nTraining complete!")
    print("Your new fine-tuned model weights are saved in: runs/detect/custom_yolov8n_finetune/weights/best.pt")

if __name__ == "__main__":
    train_model()
