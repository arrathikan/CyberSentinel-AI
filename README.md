# 🛡️ CyberSentinel AI
### AI-Powered Cyberattack Detection System

**Machine Learning | Deep Learning | Cybersecurity | FastAPI | Python**

CyberSentinel AI is an AI-powered network intrusion detection system designed to identify potentially malicious network traffic using Machine Learning and Deep Learning techniques.

The system aims to classify network traffic into two categories: **Benign (Normal Traffic)** and **Attack (Malicious Traffic)**.

The project combines data preprocessing, exploratory data analysis, machine learning model training, performance evaluation, API development, and an interactive dashboard to demonstrate an end-to-end AI/ML workflow.

> 🚧 **Project Status: In Development**  
> This project is currently being developed. Features and model results will be updated as implementation progresses.

---

## 🎯 Project Objectives

- Develop an intelligent system to detect cyberattacks from network traffic data.
- Analyze cybersecurity datasets and identify important traffic features.
- Implement and compare traditional Machine Learning and Deep Learning models.
- Evaluate classification performance using standard metrics.
- Deploy the best-performing model through a REST API.
- Build an interactive dashboard to visualize predictions and model performance.
- Demonstrate practical applications of AI in cybersecurity.

## 🚀 Key Features

The following capabilities are planned for the project:

- **Network Traffic Analysis:** Analyze network traffic records to identify suspicious behavior.
- **Binary Classification:** Predict whether network traffic is benign or malicious.
- **Data Preprocessing:** Handle missing values, duplicate records, categorical variables, and feature scaling.
- **Exploratory Data Analysis:** Visualize traffic patterns, feature distributions, and class imbalance.
- **Multiple ML Models:** Train and compare several classification algorithms.
- **Model Evaluation:** Measure classification performance using Accuracy, Precision, Recall, F1-score, and ROC-AUC.
- **Prediction API:** Serve trained models using FastAPI.
- **Interactive Dashboard:** Display predictions, performance metrics, and traffic analysis.
- **Containerization:** Package the application using Docker for reproducible deployment.

---

## 🧠 Machine Learning Models

The project plans to implement and compare the following algorithms:

| Model | Purpose |
|---|---|
| Logistic Regression | Establish a baseline classification model |
| Random Forest | Identify nonlinear patterns using an ensemble of decision trees |
| XGBoost | Improve classification using gradient-boosted decision trees |
| Neural Network | Explore deep learning for network traffic classification |

The models will be evaluated using a consistent test dataset to identify the most suitable approach.

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn, XGBoost |
| Deep Learning | TensorFlow, Keras |
| Data Visualization | Matplotlib, Seaborn |
| Model Serialization | Joblib |
| Backend API | FastAPI, Uvicorn |
| Data Validation | Pydantic |
| Development Environment | VS Code, Jupyter Notebook |
| Version Control | Git, GitHub |
| Deployment | Docker |
| Dashboard | Streamlit (Planned) |

---

## 🏗️ System Architecture

The planned architecture follows an end-to-end Machine Learning pipeline.

```text
              Network Traffic Dataset
                        |
                        v
                Data Preprocessing
                        |
                        v
              Exploratory Data Analysis
                        |
                        v
              Feature Engineering
                        |
                        v
                  Model Training
                        |
           +------------+------------+
           |            |            |
           v            v            v
        Logistic      Random       XGBoost
       Regression     Forest
           |            |            |
           +------------+------------+
                        |
                  Neural Network
                        |
                        v
                 Model Evaluation
                        |
                        v
                Best Model Selection
                        |
                        v
                 Saved ML Model
                        |
                        v
                    FastAPI
                        |
                        v
              Interactive Dashboard
                        |
                        v
                 Prediction Result
                Benign / Attack
```

## 📁 Proposed Project Structure

```text
CyberSentinel-AI/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   └── exploratory_analysis.ipynb
│
├── src/
│   ├── preprocessing.py
│   ├── feature_engineering.py
│   ├── train_model.py
│   ├── evaluate_model.py
│   └── predict.py
│
├── models/
│   └── .gitkeep
│
├── api/
│   └── main.py
│
├── dashboard/
│   └── app.py
│
├── requirements.txt
├── Dockerfile
├── .gitignore
├── LICENSE
└── README.md
```

> This structure represents the intended organization. Some directories and files may not exist until their corresponding development stages are completed.

---

## 📊 Dataset

CyberSentinel AI is designed to work with publicly available network intrusion detection datasets.

Potential datasets include:

- **CIC-IDS2017:** Network traffic containing benign and different types of malicious activity.
- **UNSW-NB15:** Network intrusion detection dataset containing normal and attack traffic.
- **CSE-CIC-IDS2018:** Cybersecurity dataset with several attack scenarios.

The selected dataset will be cleaned and transformed into a binary classification problem.

| Original Label | Binary Label |
|---|---|
| Benign / Normal | 0 |
| Attack / Malicious | 1 |

The final dataset and preprocessing decisions will be documented as the project progresses.

---

## 📈 Model Evaluation

The trained models will be compared using the following metrics:

| Metric | Description |
|---|---|
| Accuracy | Overall proportion of correct predictions |
| Precision | Proportion of predicted attacks that are actual attacks |
| Recall | Proportion of actual attacks correctly detected |
| F1-Score | Harmonic mean of Precision and Recall |
| ROC-AUC | Measures how well the model separates the classes across thresholds |
| Confusion Matrix | Displays correct and incorrect classifications |

Special attention will be given to **Recall and F1-score**, since missed cyberattacks and false alarms are important considerations in intrusion detection.

Model performance results will be published after training and evaluation.

---

## ⚙️ Installation and Setup

The following setup describes the planned Python development environment.

### 1. Clone the Repository

```bash
git clone https://github.com/arrathikan/CyberSentinel-AI.git
cd CyberSentinel-AI
```

> Replace the repository URL if the final GitHub repository name differs.

### 2. Create a Virtual Environment

For macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

For Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run Model Training

Once the training module has been implemented:

```bash
python src/train_model.py
```

### 5. Start the API

Once the FastAPI application has been implemented:

```bash
uvicorn api.main:app --reload
```

Expected local API address:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

### 6. Launch the Dashboard

Once the Streamlit dashboard has been implemented:

```bash
streamlit run dashboard/app.py
```

**Note:** The training, API, and dashboard commands will become functional as the corresponding source files are implemented.

---

## 🔍 Example Prediction

The following is an illustrative example of the planned prediction output, not a verified result from a trained model.

```json
{
  "prediction": "Attack",
  "class_label": 1,
  "confidence": 0.96
}
```

Prediction confidence will be included only when supported and appropriately evaluated for the selected model.

---

## 🗺️ Development Roadmap

- [ ] Set up the project environment and repository structure
- [ ] Download and explore the selected cybersecurity dataset
- [ ] Clean and preprocess network traffic data
- [ ] Perform exploratory data analysis
- [ ] Implement feature engineering and feature selection
- [ ] Train Logistic Regression and Random Forest models
- [ ] Train and optimize an XGBoost classifier
- [ ] Develop a TensorFlow neural network
- [ ] Evaluate and compare model performance
- [ ] Save the best-performing model
- [ ] Develop a FastAPI prediction service
- [ ] Build an interactive dashboard
- [ ] Containerize the application using Docker
- [ ] Perform integration testing and finalize documentation

## 🔮 Future Enhancements

Potential future improvements include:

- Multi-class cyberattack classification.
- Real-time network traffic monitoring.
- Explainable AI using SHAP feature analysis.
- Automated model retraining and evaluation.
- Model drift monitoring and anomaly detection.
- Integration with security monitoring platforms.
- Cloud deployment and scalable inference.

---

## 👨‍💻 Author

**Aravinthan Arrathikasarma**

AI/ML Enthusiast | Computer Science Undergraduate

- **GitHub:** [arrathikan](https://github.com/arrathikan)
- **LinkedIn:** [Aravinthan Arrathikasarma](https://www.linkedin.com/in/aravinthan-arrathikasarma/)

---

## ⚠️ Disclaimer

CyberSentinel AI is an educational and portfolio project intended for cybersecurity research and defensive applications.

Machine learning predictions are not guaranteed to identify every cyberattack. The system should not be considered a replacement for production-grade security monitoring or professional security analysis.

---

⭐ If you find this project interesting, consider giving the repository a star!

**CyberSentinel AI — Applying Artificial Intelligence to Smarter Cybersecurity.**
