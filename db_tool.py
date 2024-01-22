from dbutils.pooled_db import PooledDB
import mysql.connector
import os

def create_connection_pool(max_size=5,mincached=1,maxcached=2,**kwargs):
    pool = PooledDB(
        creator=mysql.connector,
        maxconnections=max_size,  # 最大连接数
        mincached=mincached,        # 最小空闲连接数
        maxcached=maxcached,       # 最大空闲连接数
        **kwargs
    )
    return pool
def execute(pool:PooledDB,sql:str,dictionary=False):
    
    connect = pool.connection()
    try:
        with connect.cursor(dictionary=dictionary) as cursor:
            cursor.execute(sql)
            result=cursor.fetchall()
            cursor.close()
            connect.commit()
            return result
    except Exception as e:
        connect.close()

