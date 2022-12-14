import requests
import time
import pandas as pd
from pandas.io.json import json_normalize
import numpy as np

# Закоммитить страны из словаря Countries, данные которых не планируем выгружать во время запуска данного цикла
from all_countries import countries


#ЗАДАЕМ НАЧАЛО/КОНЕЦ ПЕРИОДА ВЫГРУЗКИ, ДЕНЬ УКАЗЫВАЕМ ЛЮБОЙ - ОН БУДЕТ ОБРЕЗАН
from datetime import timedelta, datetime
start_date = datetime(year=2021, month=1, day=1)
end_date = datetime(year=2022, month=1, day=1)

# ВЫВОД УНИКАЛЬНЫХ ЗНАЧЕНИЙ

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def periods():
    tmp=[]
    for single_date in daterange(start_date, end_date):
        if single_date in tmp:
            continue
        else:
            value = single_date.strftime("%Y%m")
            tmp.append(value)
            tmp = list(set(tmp))
            tmp.sort()
    return tmp

def return_json(URL):
    flag=0

    while flag == 0:
        response = requests.get(URL)

# Без премиум лицензии, в Comtrade установлен лимит на 100 запросов к api в час с одного IP-адреса.
# При запуске скрипта в банковском контуре, без возможности менять IP каждые n минут, необходимо приостанавливать работу петли на час

        if response.status_code == 409:
            print('Hourly usage limit of 100 actions reached')
            time.sleep(3601)
        elif response.status_code == 200:
            try:
                json_obj = response.json()
                flag+=1
            except json.decoder.JSONDecodeError as e2:
                flag +=1
                return "Error: " + str(e2)
    else:
         return json_obj

def get_import(period, country_code):
    pre_url = "http://comtrade.un.org/api//get/plus?max=100000&type=C&freq=M&px=HS&ps={}&r={}&p=all&rg={}&cc=AG4&fmt=json"
    url_import = pre_url.format(period, country_code, 1)
    response_import = return_json(url_import)
    df_import = json_normalize(response_import['dataset'])
    return df_import

def get_export(period, country_code):
    pre_url = "http://comtrade.un.org/api//get/plus?max=100000&type=C&freq=M&px=HS&ps={}&r={}&p=all&rg={}&cc=AG4&fmt=json"
    url_export = pre_url.format(period, country_code, 2)
    response_export = return_json(url_export)
    df_export = json_normalize(response_export['dataset'])
    return df_export

def create_month_df(period, country_code):
    # periods = periods()

    fl=0
    df4 = pd.DataFrame([])

# При запросах к апи Comtrade некоторые месяцы могут возвращать пустые датасеты, но после паузы и повторного запроса давать корректный результат
# Чтобы избежать подобной ошибки при возврате пустого датасета выполняется повторный запрос спустя 20 секунд
# Датасет считается пустым только двух безуспешных попыток получить данные месяцу N

    while fl<2:
        df_import = get_import(period, country_code)
        time.sleep(10)
        df_export = get_export(period, country_code)

        if df_import.empty | df_export.empty:
            fl+=1
            time.sleep(20)
        else:
            df_import = df_import[["TradeValue", "aggrLevel", "motDesc", "cmdCode", "cmdDescE", "estCode", "period", "ptTitle", "rt3ISO", "rtCode", "rtTitle", "yr"]]
            df_import2 = df_import.reindex(
                columns=["TradeValue", "aggrLevel", "motDesc", "cmdCode", "cmdDescE", "estCode", "period", "ptTitle", "rt3ISO", "rtCode", "rtTitle", "yr"])
            df_import3 = df_import2[~df_import2['ptTitle'].isin(["World", "Areas, nes"])]
            df_import3.loc[:, 'Trade_flow'] = 'Import'


            df_export = df_export[["TradeValue", "aggrLevel", "motDesc", "cmdCode", "cmdDescE", "estCode", "period", "ptTitle", "rt3ISO", "rtCode", "rtTitle", "yr"]]
            df_export2 = df_export.reindex(
                columns=["TradeValue", "aggrLevel", "motDesc", "cmdCode", "cmdDescE", "estCode", "period", "ptTitle", "rt3ISO", "rtCode", "rtTitle", "yr"])
            df_export3 = df_export2[~df_export2['ptTitle'].isin(["World", "Areas, nes"])]
            df_export3.loc[:, 'Trade_flow'] = 'Export'

            new_list = [df_import3, df_export3]
            df = pd.concat(new_list)

        # df2 = df[df['motDesc'] == "TOTAL MOT"]
            df2 = df.drop(['aggrLevel', 'motDesc'], axis=1)
            df3 = df2.groupby(['cmdCode', 'cmdDescE', 'estCode', 'period', 'ptTitle', 'rt3ISO', 'rtCode', 'rtTitle', 'yr', 'Trade_flow'])['TradeValue'].max().reset_index()
            df4 = df3.drop_duplicates()
            fl+=2

    else:
        return df4


def create_multiple_months_df(country_code, country_name):
    months_periods = periods()
    month_df_test = create_month_df(months_periods[0], country_code)
    path_file = f"C:/comtrade_extractions/comtrade_{country_name}.csv"

# Если первый месяц выбранного периода пустой (после двух попыток подключения), мы относим страну N к НЕимеющей информации об импорте\экспорте

    if month_df_test.empty:

        print(f"There is no dataset for {country_name}")
    else:
        for index, value in enumerate(months_periods):
            month_df = create_month_df(value, country_code)
            if index == 0:
                month_df_test.to_csv(path_or_buf=path_file, index=False, sep=';', decimal='.', header=True, mode='a', encoding='utf-8')
                time.sleep(5)
            else:
                month_df.to_csv(path_or_buf=path_file, index=False, sep=';', decimal='.', header=False, mode='a', encoding='utf-8')
                time.sleep(5)
        else:
            print(f"{country_name} is Done!")


# Перебираем страны из словаря All_countries

for key in countries:
    create_multiple_months_df(key, countries[key])




