import joblib

model = joblib.load("gesture_model.pkl")
print(model.get_params())