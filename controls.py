import db_tool
import os
from dbutils.pooled_db import PooledDB
import threading
import time
import requests
import random
from tenacity import retry, stop_after_attempt,retry_if_exception_type,wait_exponential_jitter

newest_job_time=""

th_size=int(os.environ.get('TH_SIZE',10)) if int(os.environ.get('TH_SIZE',10))>2* os.cpu_count() else 2* os.cpu_count()
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

def get_last_selectable_time(time_str:str):
    [date,time]=time_str.split(" ")
    [month,day]=date.split("-")
    if time == '10':
        # 取前一天的19点
        return f"{month}-{int(day)-1} 19"
    if time == '14':
        # 取当天10点
        return f"{day} 10"
    if time == '19':
        # 取当天14点
        return f"{day} 14"
def get_push_result(pool:PooledDB,file_path:str):
    # 读取file_path的内容
    with open(file_path,'r') as f:
        content=f.read()
    last_selectable_time=get_last_selectable_time(newest_job_time)
    # 将文本内的$1替换成newest_job_time
    content=content.replace('$1',newest_job_time)
    # 将文本内的$2替换成last_selectable_time
    content=content.replace('$2',last_selectable_time)
    # 将文件内容变成sql来进行执行
    result=db_tool.execute(pool,content,header=True)
    return result
def get_job_id(pool: PooledDB):
    result = db_tool.execute(pool, "select zhiwei_daima from provincial_exam")
    job_id_list=[item[0] for item in result]
    set1=set(job_id_list)

    newest_job_time=get_result(job_id_list[0]).get('jzsj')
    done = db_tool.execute(pool,f"select zhiwei_daima from provincial_exam_status where jzsj='{newest_job_time}'")
    done_list=[item[0] for item in done]
    set2=set(done_list)
    return list(set1-set2)

    
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
        result=get_result(job_id)
        bkrs=result.get('bkrs')
        jzsj=result.get('jzsj')
        db_tool.execute(db_pool,f"insert into provincial_exam_status(zhiwei_daima,bkrs,jzsj) values ('{job_id}',{bkrs},'{jzsj}')")
        # time.sleep(3)
def list_to_markdown_table(data):
    # 处理表头
    header = "|".join(map(str, data[0]))
    header_line = "|".join(["---"] * len(data[0]))

    # 处理数据行
    rows = []
    for row in data[1:]:
        row_str = "|".join(map(str, row))
        rows.append(row_str)
    row_data='\n'.join(rows)
    # 拼接成Markdown表格
    markdown_table = f"{header}\n{header_line}\n{row_data}"

    return markdown_table
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
        result=get_push_result(db_pool,'push.sql')
        data=list_to_markdown_table(result)
        send_message(os.environ.get("PUSH_TOKEN"),"省考爬取结束",data)

    