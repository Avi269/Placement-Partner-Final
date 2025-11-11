"""
Training Script for Custom Resume Parser Model

This script shows how to fine-tune a language model on resume parsing data.
"""

import json
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling
)
from datasets import Dataset
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "base_model": "distilgpt2",  # Can use: gpt2, distilgpt2, facebook/opt-350m
    "output_dir": "./resume_parser_model",
    "num_epochs": 3,
    "batch_size": 4,
    "learning_rate": 5e-5,
    "max_length": 512,
}

# ============================================================================
# SAMPLE TRAINING DATA
# ============================================================================

SAMPLE_DATA = [
    {
        "input": """Extract information from this resume:

John Doe
Email: john.doe@email.com
Phone: +1 (555) 123-4567

EDUCATION
Bachelor of Science in Computer Science
MIT, 2018-2022, GPA: 3.8/4.0

EXPERIENCE
Software Engineer at Google
June 2022 - Present
- Developed scalable web applications using Python and Django
- Implemented machine learning models for recommendation systems
- Led a team of 3 junior developers

SKILLS
Python, Django, JavaScript, React, Machine Learning, AWS, Docker, SQL""",
        
        "output": """{
  "name": "John Doe",
  "email": "john.doe@email.com",
  "phone": "+1 (555) 123-4567",
  "education": ["Bachelor of Science in Computer Science, MIT, 2018-2022, GPA: 3.8/4.0"],
  "experience": ["Software Engineer at Google, June 2022 - Present"],
  "skills": ["Python", "Django", "JavaScript", "React", "Machine Learning", "AWS", "Docker", "SQL"],
  "parsed_text": "John Doe..."
}"""
    },
    # Add more training examples here...
]

# ============================================================================
# DATA PREPARATION
# ============================================================================

def prepare_training_data(data_list):
    """Convert training data to model-friendly format"""
    formatted_data = []
    
    for item in data_list:
        # Create a prompt-response pair
        text = f"{item['input']}\n\nExtracted Data:\n{item['output']}<|endoftext|>"
        formatted_data.append({"text": text})
    
    return formatted_data

def create_dataset(formatted_data, tokenizer):
    """Create a HuggingFace dataset"""
    dataset = Dataset.from_list(formatted_data)
    
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=CONFIG["max_length"],
            padding="max_length"
        )
    
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    
    return tokenized_dataset

# ============================================================================
# TRAINING FUNCTION
# ============================================================================

def train_model():
    """Main training function"""
    print("=" * 60)
    print("Resume Parser Model Training")
    print("=" * 60)
    
    # Load tokenizer and model
    print(f"\n[1/5] Loading base model: {CONFIG['base_model']}...")
    tokenizer = AutoTokenizer.from_pretrained(CONFIG["base_model"])
    model = AutoModelForCausalLM.from_pretrained(CONFIG["base_model"])
    
    # Set padding token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = model.config.eos_token_id
    
    print("✓ Model loaded successfully")
    
    # Prepare training data
    print("\n[2/5] Preparing training data...")
    formatted_data = prepare_training_data(SAMPLE_DATA)
    train_dataset = create_dataset(formatted_data, tokenizer)
    print(f"✓ Training dataset prepared ({len(train_dataset)} examples)")
    
    # Setup training arguments
    print("\n[3/5] Setting up training configuration...")
    training_args = TrainingArguments(
        output_dir=CONFIG["output_dir"],
        num_train_epochs=CONFIG["num_epochs"],
        per_device_train_batch_size=CONFIG["batch_size"],
        learning_rate=CONFIG["learning_rate"],
        warmup_steps=100,
        logging_steps=50,
        save_steps=500,
        save_total_limit=2,
        prediction_loss_only=True,
        report_to="none",  # Disable wandb/tensorboard
    )
    print("✓ Training configuration ready")
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False  # We're doing causal language modeling, not masked
    )
    
    # Initialize trainer
    print("\n[4/5] Initializing trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )
    print("✓ Trainer initialized")
    
    # Train!
    print("\n[5/5] Starting training...")
    print("This may take a while depending on your hardware...")
    trainer.train()
    
    # Save model
    print(f"\n✓ Training complete! Saving model to {CONFIG['output_dir']}")
    model.save_pretrained(CONFIG["output_dir"])
    tokenizer.save_pretrained(CONFIG["output_dir"])
    
    print("\n" + "=" * 60)
    print("SUCCESS! Model trained and saved!")
    print("=" * 60)
    print(f"\nModel location: {CONFIG['output_dir']}")
    print("\nNext steps:")
    print("1. Update core/model_backends.py to use your custom model")
    print("2. Set: CustomModelBackend('./resume_parser_model')")
    print("3. Restart your Django server")
    print("\n✅ Done!")

# ============================================================================
# LOAD YOUR OWN DATA
# ============================================================================

def load_training_data_from_file(filepath):
    """
    Load training data from a JSON file
    
    Expected format:
    [
        {
            "input": "resume text...",
            "output": "extracted JSON..."
        },
        ...
    ]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CUSTOM MODEL TRAINING SCRIPT")
    print("=" * 60)
    print("\nThis script will train a custom resume parser model.")
    print(f"Using base model: {CONFIG['base_model']}")
    print(f"Training examples: {len(SAMPLE_DATA)}")
    print(f"Output directory: {CONFIG['output_dir']}")
    
    # Check if custom training data exists
    if os.path.exists("training_data.json"):
        print("\n✓ Found training_data.json - using custom data")
        SAMPLE_DATA = load_training_data_from_file("training_data.json")
        print(f"  Loaded {len(SAMPLE_DATA)} training examples")
    else:
        print("\n⚠ No training_data.json found - using sample data")
        print("  To use your own data, create training_data.json")
    
    # Confirm before training
    response = input("\nStart training? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        try:
            train_model()
        except KeyboardInterrupt:
            print("\n\n⚠ Training interrupted by user")
        except Exception as e:
            print(f"\n✗ Training failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nTraining cancelled.")

# ============================================================================
# TESTING YOUR MODEL
# ============================================================================

def test_trained_model():
    """Test your trained model"""
    print("\n" + "=" * 60)
    print("TESTING TRAINED MODEL")
    print("=" * 60)
    
    model_path = CONFIG["output_dir"]
    
    if not os.path.exists(model_path):
        print(f"✗ Model not found at {model_path}")
        print("  Train the model first!")
        return
    
    print(f"\nLoading model from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path)
    
    test_input = """Extract information from this resume:

Jane Smith
jane.smith@email.com
+1-555-987-6543

Skills: Python, React, AWS, Docker

Education: BS Computer Science, 2020-2024"""
    
    print("\nTest Input:")
    print(test_input)
    print("\nGenerating output...")
    
    inputs = tokenizer(test_input, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    print("\nModel Output:")
    print(result)
    print("\n✓ Test complete!")

# Uncomment to test after training:
# test_trained_model()
