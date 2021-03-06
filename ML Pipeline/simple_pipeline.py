import json

import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import shap

from file_manager import FileManager


def main_pipeline():
    fm = FileManager(output_path='output_data')

    # load data

    validation_data = pd.read_parquet('META FINAL DATA/gan_1.parquet')

    shap_dfs = []
    pred_dfs = []
    files = [f'gan_{i}.parquet' for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]]
    for iter, f_name in enumerate(files):
        data = pd.read_parquet(f'META FINAL DATA/{f_name}')

        X = data.drop(['Approval', 'Race'], axis=1)
        y = data[['Approval']]

        # split data (for training and testing)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

        # train model
        model = XGBClassifier(n_estimators=500, random_state=42)
        model.fit(X_train.values, y_train.values)

        # get model preds
        preds = pd.DataFrame(model.predict(X_test), columns=['target_pred'])

        y_train.rename(columns={0: 'target_train'})
        y_train.columns = y_train.columns.astype(str)
        y_test.rename(columns={0: 'target_test'})
        y_test.columns = y_test.columns.astype(str)

        accuracy = accuracy_score(y_test, model.predict(X_test))

        vd_no_leak = validation_data.drop(['Approval', 'Race'], axis=1)

        validation_pred = pd.DataFrame(model.predict(vd_no_leak.values), columns=['Pred'], index=validation_data.index)
        validation_pred['Race'] = validation_data['Race'].values
        validation_pred['Model Num'] = iter

        explainer = shap.Explainer(model)
        shap_values = explainer(vd_no_leak)
        shap_df = pd.DataFrame(shap_values.values, columns=vd_no_leak.columns, index=vd_no_leak.index)
        shap_df['base_value'] = shap_values.base_values
        shap_df['outcome'] = shap_df.values.sum(axis=1)
        shap_df['Race'] = validation_data['Race'].values
        shap_df['Model Num'] = iter

        shap_dfs.append(shap_df)
        pred_dfs.append(validation_pred)

    all_preds = pd.concat(pred_dfs)
    all_shap = pd.concat(shap_dfs)

    group_shap_df = all_shap.drop('Race', axis=1).groupby('Model Num').apply(lambda x: x.abs().sum())
    group_shap_df['Model Num'] = list(group_shap_df.index)

    all_preds.to_parquet('preds.parquet')
    all_shap.to_parquet('shap.parquet')
    group_shap_df.to_parquet('group_shap.parquet')


main_pipeline()
