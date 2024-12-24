from flask import Flask, g, session
import re #用于匹配主域名/IP地址开头的任意长度的URL地址

from flask import render_template, url_for, request
import requests
from datetime import datetime, timedelta
from jijianduankou import app, db
import sqlalchemy as sa
import psycopg2

# select 序号, kaishi, jieshu, nv_port1, nv_port2, nv_port3, nv_port4 from cx_duankou_flow where riqi = :cha_dt;
sql_bendi = """ \
    select 序号, kaishi, jieshu, nv_port1, nv_port2, nv_port3, nv_port4 from cx_duankou_flow where riqi = :cha_dt;
    """

# 当前小时点的前8小时、前16小时，前24小时
sql_bendi_1 = """ \
    select 序号, kaishi, jieshu, nv_port1, nv_port2, nv_port3, nv_port4 
      from cx_duankou_flow 
     where riqi = :cha_dt 
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) <8
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) >=0;
    """
sql_bendi_2 = """ \
    select 序号, kaishi, jieshu, nv_port1, nv_port2, nv_port3, nv_port4 
      from cx_duankou_flow 
     where riqi = :cha_dt 
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) <16
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) >=8;
    """
sql_bendi_3 = """ \
    select 序号, kaishi, jieshu, nv_port1, nv_port2, nv_port3, nv_port4 
      from cx_duankou_flow 
     where riqi = :cha_dt 
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) <24
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) >=16;
    """
sql_bendi_4 = """ \
    select 序号, kaishi, jieshu, nv_port1, nv_port2, nv_port3, nv_port4 
      from cx_duankou_flow 
     where riqi = :cha_dt 
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) <8
       and strftime('%H', time(datetime('now', 'localtime'))) - strftime('%H', kaishi) >=0;
    """

sql_bendi_ = """\
    select w.序号, w.kaishi, w.jieshu,
    case when w.nv_port1*1 = 0 then '-    ' else w.nv_port1 end as nv_port1,
    case when w.nv_port2*1 = 0 then '-    ' else w.nv_port2 end as nv_port2,
    case when w.nv_port3*1 = 0 then '-    ' else w.nv_port3 end as nv_port3,
    case when w.nv_port4*1 = 0 then '-    ' else w.nv_port4 end as nv_port4
    from (
    select st.序号, st.时间开始 as kaishi, st.时间结束 as jieshu,
    substr(sum(case when ht.jiekou='端口_1' and time(ht.paqu_dt) between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)||"     ", 1, 5) as nv_port1,
    substr(sum(case when ht.jiekou='端口_2' and time(ht.paqu_dt) between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)||"     ", 1, 5) as nv_port2,
    substr(sum(case when ht.jiekou='端口_3' and time(ht.paqu_dt) between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)||"     ", 1, 5) as nv_port3,
    substr(sum(case when ht.jiekou='端口_4' and time(ht.paqu_dt) between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)||"     ", 1, 5) as nv_port4
    from 
    shikebiao_tb as st,
    (
    select h1.id, h1.paqu_dt, h1.fas_zijie, h1.jiekou, 
    case 
    when h1.jiekou='端口_1' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_1')) - h1.fas_zijie)/1024/1024,0) 
    when h1.jiekou='端口_2' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_2')) - h1.fas_zijie)/1024/1024,0) 
    when h1.jiekou='端口_3' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_3')) - h1.fas_zijie)/1024/1024,0) 
    when h1.jiekou='端口_4' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_4')) - h1.fas_zijie)/1024/1024,0) 
    else 0 end as 端口_用量
    from hua_paqu_lt_tb as h1
    where date(h1.paqu_dt) = :cha_dt
    ) as ht
    group by 1,2,3
    ) as w
    """

sql_huawei = """\
    select w.序号, w.kaishi, w.jieshu,
    case when w.nv_port1='0    ' then '-    ' else w.nv_port1::varchar end as nv_port1,
    case when w.nv_port2='0    ' then '-    ' else w.nv_port2::varchar end as nv_port2,
    case when w.nv_port3='0    ' then '-    ' else w.nv_port3::varchar end as nv_port3,
    case when w.nv_port4='0    ' then '-    ' else w.nv_port4::varchar end as nv_port4
    from (
    select st.序号, st.时间开始 as kaishi, st.时间结束 as jieshu,
    rpad(sum(case when ht.jiekou='端口_1' and ht.paqu_dt::time between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)::text, 4, '-') as nv_port1,
    rpad(sum(case when ht.jiekou='端口_2' and ht.paqu_dt::time between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)::text, 4, '-') as nv_port2,
    rpad(sum(case when ht.jiekou='端口_3' and ht.paqu_dt::time between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)::text, 4, ' ') as nv_port3,
    rpad(sum(case when ht.jiekou='端口_4' and ht.paqu_dt::time between st.时间开始 and st.时间结束 then ht.端口_用量 else 0 end)::text, 4, ' ') as nv_port4
    from 
    shikebiao_tb as st,
    (
    select h1.id, h1.paqu_dt, h1.fas_zijie, h1.jiekou, 
    case 
    when h1.jiekou='端口_1' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_1')) - h1.fas_zijie)/1024/1024,0) 
    when h1.jiekou='端口_2' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_2')) - h1.fas_zijie)/1024/1024,0) 
    when h1.jiekou='端口_3' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_3')) - h1.fas_zijie)/1024/1024,0) 
    when h1.jiekou='端口_4' then round(((select h2.fas_zijie from hua_paqu_lt_tb as h2 where h2.id=(select min(h3.id) from hua_paqu_lt_tb as h3 where h1.id<h3.id and h3.jiekou='端口_4')) - h1.fas_zijie)/1024/1024,0) 
    else 0 end as 端口_用量
    from hua_paqu_lt_tb as h1
    where date(h1.paqu_dt) = :cha_dt
    ) as ht
    group by 1,2,3
    ) as w
    """

'''
@app.route('/chaxun')
@app.route('/chaxun/<riqi>')
def index(riqi = None, xiaoshi=None):
  now_dt = datetime.now().date()


  if riqi is None:
    chaxun_dt = now_dt
  elif riqi == "前第1天":
    chaxun_dt = now_dt - timedelta(days=1)
  elif riqi == "前第2天":
    chaxun_dt = now_dt - timedelta(days=2)
  elif riqi == "前第3天":
    chaxun_dt = now_dt - timedelta(days=3)
  else:
    #chaxun_dt = datetime.strptime(riqi, '%Y-%m-%d').date()
    try:
      chaxun_dt = datetime.strptime(riqi, '%Y-%m-%d').date()
    except Exception as e:
      print("查询日期格式错误", e)
      chaxun_dt = now_dt
    
  
  chaxun_dt_s = datetime.strftime(chaxun_dt, '%m-%d')
  data = [{'cha_dt': chaxun_dt, }]
  res = db.session.execute(sa.text(sql_bendi), data)
  #res = db.session.execute(sa.text(sql_huawei), data)
  
  netvalues = []
  for i in res:
    netvalues.append(
      {
        "riqi": chaxun_dt_s,
        "kaishi": str(i[1])[:5],
        "jieshu": str(i[2])[:5],
        "nv_port1": i[3],
        "nv_port2": i[4],
        "nv_port3": i[5],
        "nv_port4": i[6],
      }
    )
  return render_template('home.html',  netvalues=netvalues, dangtian = now_dt, chaxun = chaxun_dt)
'''


@app.route('/chaxun')
@app.route('/chaxun/<riqi>/<xiaoshi>')
def index(riqi = None, xiaoshi=None):
  now_dt = datetime.now().date()


  if riqi is None:
    chaxun_dt = now_dt
    data = [{'cha_dt': chaxun_dt, }]
    if xiaoshi is None or xiaoshi == "当前的8小时前":
      res = db.session.execute(sa.text(sql_bendi_1), data)

    elif xiaoshi == "当前的16小时前":
      res = db.session.execute(sa.text(sql_bendi_2), data)
      #print(url_for('index', riqi, xiaoshi))
    elif xiaoshi == "当前的24小时前":
      res = db.session.execute(sa.text(sql_bendi_3), data)


  elif riqi == "前第1天":
    chaxun_dt = now_dt - timedelta(days=1)
    data = [{'cha_dt': chaxun_dt, }]
    if xiaoshi is None or xiaoshi == "当前的8小时前":
      res = db.session.execute(sa.text(sql_bendi_1), data)
    elif xiaoshi == "当前的16小时前":
      res = db.session.execute(sa.text(sql_bendi_2), data)
    elif xiaoshi == "当前的24小时前":
      res = db.session.execute(sa.text(sql_bendi_3), data)
  elif riqi == "前第2天":
    chaxun_dt = now_dt - timedelta(days=2)
    data = [{'cha_dt': chaxun_dt, }]
    if xiaoshi is None or xiaoshi == "当前的8小时前":
      res = db.session.execute(sa.text(sql_bendi_1), data)
    elif xiaoshi == "当前的16小时前":
      res = db.session.execute(sa.text(sql_bendi_2), data)
    elif xiaoshi == "当前的24小时前":
      res = db.session.execute(sa.text(sql_bendi_3), data)
  elif riqi == "前第3天":
    chaxun_dt = now_dt - timedelta(days=3)
    data = [{'cha_dt': chaxun_dt, }]
    if xiaoshi is None or xiaoshi == "当前的8小时前":
      res = db.session.execute(sa.text(sql_bendi_1), data)
    elif xiaoshi == "当前的16小时前":
      res = db.session.execute(sa.text(sql_bendi_2), data)
    elif xiaoshi == "当前的24小时前":
      res = db.session.execute(sa.text(sql_bendi_3), data)
  else:
    #chaxun_dt = datetime.strptime(riqi, '%Y-%m-%d').date()
    try:
      chaxun_dt = datetime.strptime(riqi, '%Y-%m-%d').date()
      data = [{'cha_dt': chaxun_dt, }]
      if xiaoshi is None or xiaoshi == "当前的8小时前":
        res = db.session.execute(sa.text(sql_bendi_1), data)
      elif xiaoshi == "当前的16小时前":
        res = db.session.execute(sa.text(sql_bendi_2), data)
      elif xiaoshi == "当前的24小时前":
        res = db.session.execute(sa.text(sql_bendi_3), data)
    except Exception as e:
      print("查询日期格式错误", e)
      chaxun_dt = now_dt
    
  
  chaxun_dt_s = datetime.strftime(chaxun_dt, '%m-%d')
  #data = [{'cha_dt': chaxun_dt, }]
  #res = db.session.execute(sa.text(sql_bendi), data)
  #res = db.session.execute(sa.text(sql_huawei), data)



  netvalues = []
  for i in res:
    netvalues.append(
      {
        "riqi": chaxun_dt_s,
        "kaishi": str(i[1])[:5],
        "jieshu": str(i[2])[:5],
        "nv_port1": i[3],
        "nv_port2": i[4],
        "nv_port3": i[5],
        "nv_port4": i[6],
      }
    )
  return render_template('home.html',  netvalues=netvalues, dangtian = now_dt, chaxun = chaxun_dt)









# 访问者的IP地址收集
# sql_iplist = "insert into iplist(vt_ip, vt_dt) values(:visit_ip, :visit_dt);"

# 使用SQLite3，
# sql_iplist = " insert into iplist(vt_ip, vt_dt) values(:visit_ip, :visit_dt);"

class Iplist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vt_ip = db.Column(db.String(30))
    vt_dt = db.Column(db.DateTime)
    vt_url = db.Column(db.Text)
    vt_mtd = db.Column(db.String(15))
    vt_std = db.Column(db.String(3))


'''
数据库创建：
CREATE TABLE "public"."iplist" (
  "vt_ip" varchar(30) COLLATE "pg_catalog"."default",
  "vt_dt" timestamp(6),
  "id" int4 NOT NULL DEFAULT nextval('iplist_ip_seq'::regclass),
  CONSTRAINT "iplist_pkey" PRIMARY KEY ("id")
)
;
'''



"""
@app.before_request
def before_request():
  # ip、日期时间、url等
  g.user_ip = request.headers.get('X-Forwarded-For') or request.remote_addr
  # visit_ip = g.user_ip
  g.vt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  
  g.url = request.url
  g.mtd = request.method

  # 重新设置g.std
  url_pattern = r"^http://123.60.36.100/.+$"
  url_match = re.match(url_pattern, request.url)
  if url_match:
    url_response = requests.get(url)
    g.std = url_response.status_code
  else:
    g.std = None
  
  vt_new = Iplist(vt_ip = g.user_ip, vt_dt = g.vt_now, vt_url = g.url, vt_mtd = g.mtd, vt_std = g.std)
  db.session.add(vt_new)
  db.session.commit()
"""


@app.before_request
def before_request():
  # ip、日期时间、url等
  g.user_ip = request.headers.get('X-Forwarded-For') or request.remote_addr
  # visit_ip = g.user_ip
  g.vt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  g.url = request.url
  g.mtd = request.method

@app.route('/iplist')
def ipdizhi():
  # return f'Your IP is: {g.user_ip}'
  return render_template('iplist.html', ipdizhi = g.user_ip, visit_dt = g.vt_now)




#
