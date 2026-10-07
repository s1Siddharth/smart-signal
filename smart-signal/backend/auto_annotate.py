import os
import shutil
import cv2
from pathlib import Path
from ultralytics import YOLO

# Original COCO classes we care about
COCO_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# New contiguous indices for our custom dataset
CUSTOM_CLASSES = {
    "car": 0,
    "motorcycle": 1,
    "bus": 2,
    "truck": 3,
}

def auto_annotate(image_dir, dataset_dir, model_path="yolov8n.pt"):
    print(f"Loading model {model_path}...")
    model = YOLO(model_path)
    
    img_dir_path = Path(image_dir)
    images_out = Path(dataset_dir) / "images" / "train"
    labels_out = Path(dataset_dir) / "labels" / "train"
    
    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)
    
    # Create data.yaml
    yaml_content = f"""path: {Path(dataset_dir).absolute().as_posix()}
train: images/train
val: images/train # Using train for val just for simplicity, split later if needed

names:
  0: car
  1: motorcycle
  2: bus
  3: truck
"""
    with open(Path(dataset_dir) / "data.yaml", "w") as f:
        f.write(yaml_content)
        
    print(f"Created dataset structure at {dataset_dir}")
    
    image_files = list(img_dir_path.glob("*.jpeg")) + list(img_dir_path.glob("*.jpg")) + list(img_dir_path.glob("*.png"))
    
    count = 0
    for img_path in image_files:
        # Load image to get dimensions
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"Could not read {img_path}")
            continue
            
        h, w = img.shape[:2]
        
        # Run inference
        results = model(img, verbose=False)[0]
        
        # Prepare label file
        label_file = labels_out / f"{img_path.stem}.txt"
        
        with open(label_file, "w") as f:
            if results.boxes:
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    if cls_id in COCO_CLASSES:
                        class_name = COCO_CLASSES[cls_id]
                        custom_id = CUSTOM_CLASSES[class_name]
                        
                        # YOLO format: cls_id x_center y_center width height (normalized)
                        xywh = box.xywh[0]
                        x_center = xywh[0] / w
                        y_center = xywh[1] / h
                        width = xywh[2] / w
                        height = xywh[3] / h
                        
                        f.write(f"{custom_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
                        
        # Copy image to dataset dir
        new_img_path = images_out / img_path.name
        shutil.copy(img_path, new_img_path)
        count += 1
        print(f"Processed {count}/{len(image_files)}: {img_path.name}")
        
    print(f"\n✅ Auto-annotation complete!")
    print(f"Dataset ready at: {dataset_dir}")
    print(f"You can now use a tool like LabelImg or MakeSense.ai to open {images_out}")
    print(f"and verify/fix the annotations in {labels_out} before training.")

if __name__ == "__main__":
    SOURCE_IMGS = r"a:\OE\img"
    DATASET_DIR = r"a:\OE\dataset"
    # Ensure you are running this from the backend dir where yolov8n.pt exists
    auto_annotate(SOURCE_IMGS, DATASET_DIR, model_path="yolov8n.pt")
