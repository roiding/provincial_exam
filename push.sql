-- 报名增长速度
select
	d.danwei_mingcheng as '单位名称',
	d.zhiwei_jianjie as '职位简介',
	d.zhaolu_renshu as '招录人数',
	c.* from (SELECT a.zhiwei_daima as '职位代码',a.bkrs as '现过审人数',b.bkrs as '上次过审人数',a.bkrs-b.bkrs as '净增长',CASE 
        WHEN b.bkrs = 0 THEN a.bkrs*100 -- 避免除数为零错误
        ELSE ROUND((a.bkrs - b.bkrs) / b.bkrs *100,1)
    END AS '增长率'
FROM
  (SELECT zhiwei_daima, bkrs FROM provincial_exam_status WHERE jzsj = '$1') AS a
LEFT JOIN
  (SELECT zhiwei_daima, bkrs FROM provincial_exam_status WHERE jzsj = '$2') AS b
ON a.zhiwei_daima = b.zhiwei_daima
) c INNER JOIN provincial_exam d on c.`职位代码`=d.zhiwei_daima
where d.zhuanye_yaoqiu_benke like "%计算机%" 
-- 	定向招录
	and d.dingxiang_zhaolu_xiangmu_fuwujiceng is null and d.dingxiang_zhaolu_xiangmu_shaoshuminzu is null and d.dingxiang_zhaolu_xiangmu_youxiucunzhuganbu is null and d.dingxiang_zhaolu_xiangmu_2024jie_biye_sheng is null
-- 	政治面貌
	and d.zhengzhi_mianmao_yaoqiu is null
--  限制地点
	and (d.kaoqu='毕节市' or d.danwei_dizhi like '毕节市%')
order by c.`增长率`;
