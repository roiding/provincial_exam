import db_tool
import os
from dbutils.pooled_db import PooledDB
import threading
import time
import requests
import random
from tenacity import retry, stop_after_attempt,retry_if_exception_type,wait_exponential_jitter

th_size=int(os.environ.get('TH_SIZE',10))
@retry(stop=stop_after_attempt(3),wait=wait_exponential_jitter(initial=30,max=300,jitter=30),retry=retry_if_exception_type(ConnectionError))
def send_message(token: str, title: str, content: str):
    '''
    发送消息
    '''
    url = f"https://sctapi.ftqq.com/{token}.send"
    body = {
        "title": title,
        "desp": content,
        "short": title,
    }
    header = {
        "Content-type": "application/json"
    }
    response = requests.post(url, json=body, headers=header)
    return response.json()

def get_job_id(pool: PooledDB):
    result = db_tool.execute(pool, "select zhiwei_daima from provincial_exam")
    job_id_list=[item[0] for item in result]
    set1=set(job_id_list)

    newest_hob_id=get_result(job_id_list[0]).get('jzsj')
    done = db_tool.execute(pool,f"select zhiwei_daima from provincial_exam_status where jzsj='{newest_hob_id}'")
    done_list=[item[0] for item in done]
    set2=set(done_list)
    return set1-set2

    
# 将一个列表切分成N份
def chunk_list(l, n):
    length=len(l)
    size=length//n
    for i in range(n):
        if i==n-1:
            yield l[i*size:]
        else:
            yield l[i*size:(i+1)*size]
@retry(wait=wait_exponential_jitter(initial=3,max=12,jitter=3))
def get_result(job_id:str):
    result=requests.post('http://gzrsks.oumakspt.com:62/tyzpwb/stuchooseexam/getPositionInfo.htm',data={'zwdm':job_id,'examid':'37ed94f6ecdb3320'})
    return result.json()
def worker(db_pool:PooledDB,job_id_list:str):
    for job_id in job_id_list:
        result=get_result(db_pool,job_id)
        bkrs=result.get('bkrs')
        jzsj=result.get('jzsj')
        result1=db_tool.execute(db_pool,f"insert into provincial_exam_status(zhiwei_daima,bkrs,jzsj) values ('{job_id}',{bkrs},'{jzsj}')")
        # time.sleep(3)
   
if __name__ == '__main__':
    db_pool = db_tool.create_connection_pool(max_size=th_size,host=os.environ.get('DB_HOST'), user=os.environ.get('DB_USERNAME'), password=os.environ.get(
        'DB_PASSWORD'), database=os.environ.get('DB_NAME'), ssl_ca=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cert.pem'))
    # 所有的jobid
    job_id_list=get_job_id(db_pool)
    # 切分成th_size份
    job_id_list=list(chunk_list(job_id_list, th_size))
    threads=[]
    for i in range(th_size):
        thread = threading.Thread(target=worker, args=(db_pool,job_id_list[i],))
        threads.append(thread)
    # 启动所有线程
    for thread in threads:
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    db_pool.close()
    if os.environ.get("PUSH_TOKEN"):
        send_message(os.environ.get("PUSH_TOKEN"),"省考爬取结束","省考爬取结束")

    