# Machine learning modules
from app.ml.features import FeatureEngineer, SOLAR_FEATURES, WIND_FEATURES
from app.ml.synthetic_dataset import generate_training_dataset
from app.ml.solar_model import SolarForecaster
from app.ml.train_solar import train_and_register_solar_model

__all__ = [
    "FeatureEngineer",
    "SOLAR_FEATURES",
    "WIND_FEATURES",
    "generate_training_dataset",
    "SolarForecaster",
    "train_and_register_solar_model",
]
