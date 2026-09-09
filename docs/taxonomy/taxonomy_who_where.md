# taxonomy_who

| node_id | case_id | is_source | node_label | role | platform | content_description |
|---------|---------|-----------|------------|------|----------|---------------------|
| C01-N0 | C01 | yes | 英国统计机构ONS | bridger | 政府/官方机构/国际组织 | ONS按周发布登记死亡人数，含完整数据来源、统计口径说明、区分和疫情有关的死亡数和无关的死亡数 |
| C01-N1 | C01 | no | V1: BBC转载 | amplifier | 新闻媒体 | 指出covid deaths are rising, BBC调整了图表类型为面积图、更改了配色、增加标题疫情死亡上升的描述、更改图例名称deaths not involving covid-19变为official covid-19、简化了坐标轴 | https://www.bbc.com/news/uk-54905018?utm_medium=organic&utm_source=yandexsmartcamera
| C01-N2 | C01 | no | V2: 个人维护的新闻社区网站 | amplifier | 个人网站/博客 | 更改了配色。简化了坐标轴。增加了注释（指出和正常相比死亡数的百分比）、通过使用灰色背景突出超额死亡部分、修改标题强化读者对"疫情导致大量超额死亡" | 
| C01-N3 | C01 | no | V3: BBC转载 | extender | 新闻媒体 | 改变标题疫情是如何影响超额死亡率，从疫情死亡上升议题加入影响超额死亡率的议题 |
| C02-N0 | C02 | yes | 美国国家海洋和大气管理局NOAA | bridger | 政府/官方机构/国际组织 | NOAA定时更新全球温度情况 |
| C02-N1 | C02 | no | V1: Tweet用户Steve Molly | transformer/adverser | 社交媒体 | 摘取其中一段数据范围，删除数据来源，加入趋势线说明全球变冷 |
| C02-N2 | C02 | no | V2: NASA | bridger | 政府/官方机构/国际组织 | 更改配色，改变title说last 9 years warmest on record |
| C02-N3 | C02 | no | V3: BBC | amplifier | 新闻媒体 | 更改配色（强化），简化坐标轴，改变标题说world set for hottest july on record，增加注释warmer than average |
| C03-N0 | C03 | yes | 美国国家健康计划项目PNHP | bridger | 政府/官方机构/国际组织 | |
| C03-N1 | C03 | no | V1: IBJ新闻媒体 | extender | 新闻媒体 | 修改配色，增加新的变量：percent growth of U.S. healthcare spending per capita美国人均医疗保健支出增长的百分比 |
| C03-N2 | C03 | no | V2: Tweet用户Calley Means白宫议员 | amplifier | 社交媒体 | 修改配色，调整纵横比（提高纵轴、缩短横轴） |
| C04-N0 | C04 | yes | INPE巴西国家空间研究院 | bridger | 政府/官方机构/国际组织 | |
| C04-N1 | C04 | no | V1: BBC | amplifier | 新闻媒体 | 截取部分数据，增加标题说去森林化率从2006年起比较高，修改配色 |
| C04-N2 | C04 | no | V2: BBC | transformer/adverser | 新闻媒体 | 拓展数据，发现下降改变标题说在去森林化率哪一年下降了，修改配色 |
| C04-N3 | C04 | no | V3: Mongabay环境保护新闻网站 | amplifier | 新闻媒体 | 修改配色，增加森林背景（红绿对比） |
| C05-N0 | C05 | yes | Wikimedia commons | bridger | 第三方数据平台 | |
| C05-N1 | C05 | no | V1: Advisor channel频道 | extender | 新闻媒体 | 引入历史关键事件议题增加注释，增加背景配图，改变标题美国通货膨胀的过去现在未来 |
| C05-N2 | C05 | no | V2: zerohedge | amplifier | 新闻媒体 | 修改配色，修改图表类型（尖尖面积图变柱状图），截取时间，增加注释（关键节点注释事件），简化坐标轴 |
| C05-N3 | C05 | no | V3: 房地产社区 | extender | 机构博客 | 修改配色，通货膨胀引入更广泛的价格议题（房地产），修改标题price inflation for all items since 1913 |
| C06-N0 | C06 | yes | newyork news | bridger | 新闻媒体 | |
| C06-N1 | C06 | no | V1: JFP news | amplifier | 新闻媒体 | 加粗注释，修改颜色 |
| C06-N2 | C06 | no | V2: Armstrong economics | transformer/adverser | 个人网站/博客 | 修改之前对比强烈的配色（让对比显得温和），改变注释 |
| C07-N0 | C07 | yes | Reutres路透社 | bridger | 新闻媒体 | |
| C07-N1 | C07 | no | V1: Ycharts | bridger | 第三方数据平台 | 修改配色，修改图表类型，从线性变为面积图，增加视觉冲击 |
| C07-N2 | C07 | no | V2: Inc新闻网站 | extender | 新闻媒体 | 修改配色，增加对比变量大学应届毕业生的失业率 |
| C08-N0 | C08 | yes | US Department of Homeland Security | bridger | 政府/官方机构/国际组织 | |
| C08-N1 | C08 | no | V1: Senator Ron Johnson's office | amplifier | 社交媒体 | 修改配色、增加注释、修改主题 |
| C08-N2 | C08 | no | V2: Senator Ron Johnson's office | amplifier | 社交媒体 | 修改数据粒度 |
| C08-N3 | C08 | no | V3: Senator Ron Johnson's office | amplifier | 社交媒体 | 增加注释 |
| C08-N4 | C08 | no | V4: Senator Ron Johnson's office | extender | 社交媒体 | 增加变量 |
| C08-N5 | C08 | no | V5: Trump team | amplifier | 社交媒体 | 通过改变标题说明这是不好的问题，然后通过调整注释，突出特朗普的政绩 |
| C09-N0 | C09 | yes | tweet发布政治图表的用户（粉丝多） | bridger | 社交媒体 | |
| C09-N1 | C09 | no | V1: 原创作者自行迭代 | extender | 社交媒体 | 添加不同种族出生率数据系列对比 |
| C09-N2 | C09 | no | V2: 原创作者自行迭代 | extender | 社交媒体 | 添加其他总统时期数据对比 |
| C09-N3 | C09 | no | V3: TCN | bridger | 社交媒体 | 修改配色，修改背景 |
| C10-N0 | C10 | yes | Wikipedia | bridger | 第三方数据平台 | |
| C10-N1 | C10 | no | V1: Climate Depot | amplifier | 新闻媒体 | 增加注释（案例一般） |
| C10-N2 | C10 | no | V2: 社区 | amplifier | 在线社区/UGC平台 | 增加注释（案例一般） |
| C11-N0 | C11 | yes | BBC | bridger | 新闻媒体 | |
| C11-N1 | C11 | no | V1: 英国气象局Met office | extender | 机构博客 | 说疫情可能导致浓度下降 |
| C11-N2 | C11 | no | V2: World Economic Forum世界经济论坛 | amplifier | 政府/官方机构/国际组织 | 修改配色，2022年将成为年平均CO2浓度首次超过工业化前水平50%的第一年 |
| C12-N0 | C12 | yes | CBP public data dashboard | bridger | 政府/官方机构/国际组织 | |
| C12-N1 | C12 | no | V1: 普通用户 | amplifier | 社交媒体 | 增加标注（颜色突出） |
| C12-N2 | C12 | no | V2: 普通用户 | amplifier | 社交媒体 | 增加标注（颜色突出） |
| C12-N3 | C12 | no | V3: 普通用户 | extender | 社交媒体 | 筛选数据变量呈现 |
| C13-N0 | C13 | yes | Swiss Policy Research (SPR)研究小组 | bridger | 科研机构 | |
| C13-N1 | C13 | no | V1: the automatic earth | amplifier | 政府/官方机构/国际组织 | 质疑疫苗安全性与有效性：反复强调"接种后刺突蛋白5个月仍在体内循环""早期接种者感染率是后期2倍""接种者病毒载量更高、更易传播"等观点，引用VAERS死亡数据、辉瑞采购协议中"长期效果未知"的条款作为支撑 |
| C13-N2 | C13 | no | V2: Swiss Policy Research (SPR)研究小组 | bridger | 科研机构 | 变为由每年变为累积，变成面积图 |
| C13-N3 | C13 | no | V3: 前身是Reddit子版块r/The_Donald，2020年因违反平台规则被封禁后，支持者迁至thedonald.win，后更名patriots.win | amplifier | 在线社区/UGC平台 | 说疫苗有害 |
| C13-N4 | C13 | no | V4: 个人运营的网站 | amplifier | 个人网站/博客 | 现在有独立的数据来源可以验证COVID-19疫苗危险性的VAERS记录 |
| C14-N0 | C14 | yes | the bell curve书 | bridger | 科研机构 | |
| C14-N1 | C14 | no | V1: IFUNNY个人用户 | amplifier | 在线社区/UGC平台 | 通过修改标题、大写注释、增加y轴，改变配色 |
| C14-N2 | C14 | no | V2: 4chan论坛匿名用户 | amplifier | 在线社区/UGC平台 | 通过增加注释，传播偏见 |
| C15-N0 | C15 | yes | wolfstreet个人网站 | bridger | 个人网站/博客 | 根据今天早些时候发布的S&P CoreLogic Case-Shiller全国房价指数，全国房价同比上涨了6.3%（未进行季节性调整）。该指数现已超过2006年7月住房泡沫1的疯狂峰值，当时它开始以壮观的方式崩溃。得益于激进和实验性的货币政策，自住房崩盘1的低点以来，房价已重新膨胀了46% |
| C15-N1 | C15 | no | V1: wolfstreet个人网站 | bridger | 个人网站/博客 | 筛选数据变量呈现 |
| C15-N2 | C15 | no | V2: wolfstreet个人网站 | bridger | 个人网站/博客 | 增加标记线引导 |
| C21-N0 | C21 | yes | 美国公益性网站The Disaster Center | bridger | 个人网站/博客 | 按年份统计了近六十年来的暴力犯罪统计率 |
| C21-N1 | C21 | no | V1: American Journal of Criminal Justice | bridger | 科研机构 | 给出了拟合后的回归趋势线以及具体直线方程的数据 |
| C21-N2 | C21 | no | V2: imgur免费图片托管（图床）和分享社区 | amplifier | 在线社区/UGC平台 | 增加了注释，缩短了时间年限（之前是1960到2020，现在只到2012），并且加了From FBI data 2012 prelimaniry estimate 的注释 |
| C21-N3 | C21 | no | V3: Sean Williams佛罗里达大学教授 | bridger | 科研机构 | 细化坐标轴的同时把每一年的数据在曲线上加重标注出来 |
| C22-N0 | C22 | yes | 弗罗里达大学选举实验室 | bridger | 科研机构 | National Turnout Rates Graph |
| C22-N1 | C22 | no | business insider媒体新闻网站（source是US Election Project） | bridger | 新闻媒体 | voter turnout，去掉了midterm数据系列，只保留presidential数据系列 |
| C22-N2 | C22 | no | V1: statista | bridger | 第三方数据平台 | 更换了颜色 |
| C22-N3 | C22 | no | V2: historyinchart个人统计网站 | extender | 个人网站/博客 | 通过对关键数据点增加历史事件关联的注释，拓展了议题The History of Voter Turnout in the US，同时通过改变背景为蓝色 |
| C23-N0 | C23 | yes | fred | bridger | 政府/官方机构/国际组织 | fred网站标题为Smoothed U.S. Recession Probabilities (RECPROUSM156N) |
| C23-N1 | C23 | no | MarketWatch新闻媒体 | extender | 新闻媒体 | 引入了股票市场议题，按照年份统计经济衰退率，同时用阴影部分做了标注，最终给出了短时间的预测。给出了议题Don't Wait For Recessions To Sell Stocks |
| C23-N2 | C23 | no | V1: visualcapitalist网站 | amplifier | 新闻媒体 | 改变了颜色，增加了注释，突出high probability of us recession |
| C23-N3 | C23 | no | V2: econbrowser（Analysis of current economic conditions and policy） | extender | 个人网站/博客 | 增加对比项，使用10年期-3个月期国债利差（蓝色）和10年期-2年期国债利差（红色）预测未来12个月的经济衰退概率，通过引入其他对比项延伸了议题 |
| C23-N4 | C23 | no | V3: Motley Fool | bridger | 机构博客 | 改变了颜色 |
| C24-N0 | C24 | yes | tradingeconomics United States Department of Labor 美国劳工统计局 | bridger | 政府/官方机构/国际组织 | tradingeconomics上没有找到原图。但是多图来源指向此来源 |
| C24-N1 | C24 | no | V1: 普通用户 | amplifier | 社交媒体 | 从1949-2021的12.01的美国居民劳动率，在2020有剧变下降 |
| C24-N2 | C24 | no | V2: University of Richmond Blogs大学论坛 | bridger | 在线社区/UGC平台 | 简化了坐标轴 |
| C24-N3 | C24 | no | V3: linkedin普通用户 | bridger | 社交媒体 | 简化了坐标轴 |
| C24-N4 | C24 | no | V4: utah.gov犹他州政府 | amplifier | 政府/官方机构/国际组织 | 在N0的基础上在1968左右的时间点加上注释，强调婴儿出生率快速上升提到了劳动参加率 |
| C25-N0 | C25 | yes | United States Department of Labor 美国劳工统计局 | bridger | 政府/官方机构/国际组织 | 近20年来的居民失业率 |
| C25-N1 | C25 | no | V1: finance.yahoo | bridger | 第三方数据平台 | 除了时间更新到最新的时间之外（只到2022）没有其他变化 |
| C25-N2 | C25 | no | V2: Mission Wealth经济组织 | amplifier | 新闻媒体 | 改变了颜色，增加了一条红色的（从2020开始暴涨有快速回跌的过程）下降的引导趋势线 |
| C25-N3 | C25 | no | V3: 维基百科 | extender | 第三方数据平台 | 引入了俄亥俄州失业率，将美国（红色）与俄亥俄州失业率（蓝色）进行对比 |
| C26-N0 | C26 | no | statista（source应该是International Monetary Fund，但是没有找到） | bridger | 第三方数据平台 | 柱状图展示2015-2022期间直接与间接的化石燃料补贴 |
| C26-N1 | C26 | no | V1: eurasiareview新闻媒体网站 | amplifier | 新闻媒体 | 更改配色，增加注释 |
| C27-N0 | C27 | yes | resoilfoundation新闻网站 | bridger | 新闻媒体 | 1830年至2010年全球能源消耗趋势 |
| C27-N1 | C27 | no | V1: peakoil论坛 | extender | 在线社区/UGC平台 | 增加了2010年之后的预测趋势，以2010为界限做分割做了标记 |
| C27-N2 | C27 | no | V2: AAPG演讲 Cindy Yeilding | bridger | 科研机构 | 较N0(V1)修改了配色 |
