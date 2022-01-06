from pyspark.sql import SparkSession
from pyspark.sql import SQLContext
from pyspark.sql import Row
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.ml.regression import LinearRegression, DecisionTreeRegressor, RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.linalg import DenseVector
import numpy as np

def string_to_list(string):
    if string == 'N/A':
        return []
    return [s.strip() for s in string.split(',')]

def convert_year(year):
    today = 2021
    if len(year) == 4:
        a = [year]
    elif len(year) == 5:
        start_year = int(year[:4])
        a = [str(y) for y in range(start_year, today + 1)]
    elif len(year) == 9:
        start_year, end_year = [int(y) for y in year.split('–')[:2]]
        a = [str(y) for y in range(start_year, end_year + 1)]
    else:
        a = []
    return [int(e) for e in a]

if __name__ == '__main__':
    spark = SparkSession.builder.appName("Machine Learning").getOrCreate()
    sc = spark.sparkContext
    sc.setLogLevel('ERROR')
    sqlContext = SQLContext(sc)
    PROCESSED_DATA_DIRECTORY = '/user/root/dataframe/'
    df = sqlContext.read.format('parquet').load('hdfs://namenode:9000' + PROCESSED_DATA_DIRECTORY)
    df = df.distinct()
    print('Number of rows:', df.count())
    print('Number of rows with null value in field Type:', df.where(F.col('Type').isNull()).count())
    TYPE_DICT = {
        'movie': 0,
        'series': 1,
        'game': -1
    }
    LIST_FEARTURE = dict()
    for key in ['Genre', 'Director', 'Writer', 'Actors', 'Language', 'Country']:
        LIST_FEARTURE[key] = df.rdd.flatMap(lambda row: string_to_list(row[key])).distinct().collect()
    print('Total:')
    for key, value in LIST_FEARTURE.items():
        print('\t', key, len(value))
    MAX_SIZE = 100
    with open('/content/director.csv', 'r') as f:
        lines = f.readlines()[1:1 + MAX_SIZE]
        LIST_FEARTURE['Director'] = [line.split(',')[0] for line in lines]
    with open('/content/writer.csv', 'r') as f:
        lines = f.readlines()[1:1 + MAX_SIZE]
        LIST_FEARTURE['Writer'] = [line.split(',')[0] for line in lines]
    with open('/content/actors.csv', 'r') as f:
        lines = f.readlines()[1:1 + MAX_SIZE]
        LIST_FEARTURE['Actors'] = [line.split(',')[0] for line in lines]
    print('Use:')
    for key, value in LIST_FEARTURE.items():
        print('\t', key, len(value))
    LIST_YEAR = df.rdd.flatMap(lambda row: convert_year(row['Year'])).distinct().collect()
    LIST_YEAR.sort()
    min_year, max_year = LIST_YEAR[0], LIST_YEAR[-1]
    YEAR_RANGE_DICT = {x: str(x * 10) + '-' + str(x * 10 + 10) for x in range(int(np.floor(min_year / 10)), int(np.ceil(max_year / 10)), 1)}

    def transform(row):
        transform_dict = dict()
        transform_dict['ID'] = row['imdbID']
        transform_dict['Rating'] = row['imdbRating']
        for key, value in LIST_FEARTURE.items():
            for v in value:
                transform_dict[key + '_' + v.replace(' ', '')] = 1 if v in row[key] else -1
        year_list = convert_year(row['Year'])
        for value in YEAR_RANGE_DICT.values():
            transform_dict['Year_' + value] = -1
        if len(year_list) >= 1:
            for i in range(int(np.floor(year_list[0] / 10)), int(np.ceil(year_list[-1] / 10)), 1):
                transform_dict['Year_' + YEAR_RANGE_DICT[i]] = 1
        try:
            transform_dict['Type'] = TYPE_DICT[row['Type']]
        except:
            transform_dict['Type'] = -1
        return Row(**transform_dict)

    transform_df = df.rdd.map(lambda row: transform(row)).toDF()
    FEATURE_COLUMNS = ['Type']
    for key, value in LIST_FEARTURE.items():
        for v in value:
            FEATURE_COLUMNS.append(key + '_' + v.replace(' ', ''))
    FEATURE_COLUMNS += ['Year_' + value for value in YEAR_RANGE_DICT.values()]
    print('Number of features:', len(FEATURE_COLUMNS))

    def merge_feature(row):
        merge_dict = dict()
        merge_dict['ID'] = row['ID']
        merge_dict['Rating'] = row['Rating']
        merge_dict['Features'] = DenseVector([row[key] for key in FEATURE_COLUMNS])
        return Row(**merge_dict)

    merge_feature_df = transform_df.rdd.map(lambda row: merge_feature(row)).toDF()
    train_df, test_df = merge_feature_df.randomSplit([0.7, 0.3])
    print('Number of train samples:', train_df.count())
    print('Number of test samples:', test_df.count())
    use_train_df = train_df.select(F.col('Rating').alias('label'), F.col('Features').alias('features'))
    use_test_df = test_df.select(F.col('Rating').alias('label'), F.col('Features').alias('features'))
    rmse_evaluator = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="rmse")
    mse_evaluator = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="mse")
    mae_evaluator = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="mae")

    # Linear
    linearRegression = LinearRegression(regParam=0.1, elasticNetParam=0.05)
    linearRegressionModel = linearRegression.fit(use_train_df)
    result_df = linearRegressionModel.transform(use_test_df)
    print('Linear Model:')
    print('Coefficients:', linearRegressionModel.coefficients)
    print('Evaluate:')
    print('\trmse', rmse_evaluator.evaluate(result_df))
    print('\tmse', mse_evaluator.evaluate(result_df))
    print('\tmae', mae_evaluator.evaluate(result_df))

    # Decision Tree
    decisionTreeRegressor = DecisionTreeRegressor()
    decisionTreeModel = decisionTreeRegressor.fit(use_train_df)
    result_df = decisionTreeModel.transform(use_test_df)
    print('Decision Tree Model:')
    print('Depth:', decisionTreeModel.depth, '; number of nodes:', decisionTreeModel.numNodes)
    print('Evaluate:')
    print('\trmse', rmse_evaluator.evaluate(result_df))
    print('\tmse', mse_evaluator.evaluate(result_df))
    print('\tmae', mae_evaluator.evaluate(result_df))

    # Random forest
    randomForestRegressor = RandomForestRegressor()
    randomForestModel = randomForestRegressor.fit(use_train_df)
    result_df = randomForestModel.transform(use_test_df)
    print('Decision Tree Model:')
    print('Number of trees:', randomForestModel.getNumTrees)
    print('Trees in forest:')
    print(randomForestModel.trees)
    print('Evaluate:')
    print('\trmse', rmse_evaluator.evaluate(result_df))
    print('\tmse', mse_evaluator.evaluate(result_df))
    print('\tmae', mae_evaluator.evaluate(result_df))
