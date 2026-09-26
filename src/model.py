from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from features import CAT, NUM
LGB_PARAMS=dict(n_estimators=300,learning_rate=0.03,num_leaves=15,min_child_samples=40,subsample=0.8,
                subsample_freq=1,colsample_bytree=0.8,reg_lambda=5,verbose=-1)
def make_logreg(C=0.1):
    pre=ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore"),CAT),("n",StandardScaler(),NUM)])
    return make_pipeline(pre,LogisticRegression(C=C,max_iter=3000))
