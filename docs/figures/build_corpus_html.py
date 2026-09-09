#!/usr/bin/env python3
"""
Build corpus_browser.html + corpus.json from taxonomy markdown tables.
All output is self-contained (single HTML file, inline CSS/JS, base64 images).
"""

import json, re, base64
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parent.parent.parent
TAX = ROOT / "docs" / "taxonomy"
OUT = Path(__file__).resolve().parent

ROLE_COLOR = {
    "bridger": "#8A8FCC", "amplifier": "#C44E42",
    "adverser": "#E0A032", "extender": "#549E9F",
}
OP_L1 = {
    "select data variables": "Data Manipulation", "add data variables": "Data Manipulation",
    "select data range": "Data Manipulation", "select time range": "Data Manipulation",
    "change data granularity": "Data Manipulation",
    "change type": "Visual Encoding", "change chart type": "Visual Encoding",
    "change color": "Visual Encoding", "add background": "Visual Encoding",
    "change visual background": "Visual Encoding",
    "simplify axis": "Visual Encoding", "simplify axis text": "Visual Encoding",
    "change aspect ratio": "Visual Encoding", "change axis scale": "Visual Encoding",
    "change title": "Textual Elements", "add annotation": "Textual Elements",
    "change annotation": "Textual Elements", "delete source": "Textual Elements",
    "change legend": "Textual Elements", "change lgd": "Textual Elements",
    "change ldg": "Textual Elements",
    "add legend": "Textual Elements", "add lgd": "Textual Elements",
}
L1_COLOR = {
    "Data Manipulation": "#D08350",
    "Visual Encoding": "#C25B8E",
    "Textual Elements": "#6AAA3A",
}
PLAT_EN = {
    "政府/官方机构/国际组织": "Official Inst.",
    "新闻媒体": "News Media", "社交媒体": "Social Media",
    "个人网站/博客": "Personal Website", "第三方数据平台": "3rd-Party Data",
    "在线社区/UGC平台": "Online Community", "科研机构": "Research Inst.",
    "机构博客": "Industry Website",
}

CASE_IMAGE_MAP = {
    "C01": "data/06_COVID_excess_deaths",
    "C02": "data/01_global_temperature",
    "C04": "data/04_amazon_deforestation",
    "C07": "data/03_civilian_unemployment",
    "C08": "data/05_FY_encounters_by_month",
    "C11": "data/02_atmospheric_CO2_concentration",
    "C17": "data/08_National_Turnout_Rates",
    "C18": "data/09_Economic_recession_probability",
}

TOPIC_EN = {
    "C01": "COVID-19 Weekly Death Registrations",
    "C02": "Global Temperature Anomaly",
    "C03": "Growth of Physicians vs. Administrators",
    "C04": "Amazon Deforestation Rate",
    "C05": "US Inflation Rate",
    "C06": "COVID-19 Case Trends",
    "C07": "US Unemployment Rate",
    "C08": "US Immigration Encounters",
    "C09": "Birth Rate & Immigration",
    "C10": "Global Climate Temperature",
    "C11": "Atmospheric CO\u2082 Concentration",
    "C12": "US Border Encounters",
    "C13": "VAERS Reported Deaths",
    "C14": "IQ Distribution Controversy",
    "C15": "US Housing Price Index",
    "C16": "Violent Crime Trends",
    "C17": "Presidential Election Turnout",
    "C18": "Economic Recession Probability",
    "C19": "Labor Force Participation Rate",
    "C20": "Civilian Unemployment Rate",
    "C21": "Fossil Fuel Subsidies",
    "C22": "Global Energy Consumption",
}

CATEGORY_EN = {
    "疫情": "Pandemic", "气候": "Climate", "政策": "Policy",
    "环境": "Environment", "金融": "Finance", "经济": "Economy",
    "移民": "Immigration", "疫苗": "Vaccine", "种族": "Race",
    "安全": "Public Safety", "能源": "Energy",
}

VIZ_TYPE_EN = {
    "面积图": "Area Chart", "柱状图": "Bar Chart", "组合图": "Combo Chart",
    "线性图": "Line Chart", "线型图": "Line Chart",
}

EVIDENCE_EN = {
    "增加叙事标题，指出deaths are rising。柱状图改为山峰面积图。简化坐标轴。更改图例名称deaths not involving covid-19变为official covid-19。原本中立的图表变得有主题":
        "Added narrative title stating 'deaths are rising'. Changed bar chart to area chart. Simplified axes. Changed legend from 'deaths not involving covid-19' to 'official covid-19'. Neutral chart became thematic.",
    "主图样式基本保留，原本中立的图表变得有主题":
        "Main chart style mostly preserved; originally neutral chart became thematic.",
    "改变标题疫情是如何影响超额死亡率，从疫情死亡上升议题加入影响超额死亡率的议题":
        "Changed title to 'how the pandemic affected excess deaths', extending topic from rising COVID deaths to excess mortality.",
    "摘取其中一段数据范围，删除数据来源，加入趋势线说明全球变冷":
        "Selected a specific data range, deleted data source, added trend line claiming 'global cooling'.",
    "更改配色，改变title说last 9 years warmest on record":
        "Changed color scheme, updated title to 'last 9 years warmest on record'.",
    "更改配色（强化），简化坐标轴，改变标题说world set for hottest july on record，增加注释warmer than average，截取数据范围":
        "Intensified colors, simplified axes, changed title to 'world set for hottest July on record', added annotation 'warmer than average', selected data range.",
    "主图样式基本保留，只是改变了配色":
        "Main chart style preserved; only color scheme changed.",
    "修改配色，调整纵横比（提高纵轴、缩短横轴）":
        "Changed color scheme, adjusted aspect ratio (stretched Y-axis, compressed X-axis).",
    "截取部分数据，增加标题说去森林化率从2006年起比较高，修改配色":
        "Selected partial data, added title stating deforestation rate highest since 2006, changed colors.",
    "拓展数据发现新趋势，发现下降改变标题说在去森林化率哪一年下降了，修改配色":
        "Extended data revealed new trend; changed title to highlight year deforestation rate fell, changed colors.",
    "修改配色，增加森林背景（红绿对比）":
        "Changed colors, added forest background image (red-green contrast).",
    "引入历史关键事件议题增加注释，增加背景配图，改变标题美国通货膨胀的过去现在未来。主图样式变丰富，原本中立的图表变得有主题":
        "Introduced historical events as annotations, added background image, changed title to 'US inflation: past, present and future'. Chart became richer and thematic.",
    "修改配色，修改图表类型（尖尖面积图变柱状图），截取时间，增加注释（关键节点注释事件），简化坐标轴":
        "Changed colors, changed chart type (area to bar), selected time range, added event annotations at key points, simplified axes.",
    "修改配色，通货膨胀引入更广泛的价格议题（房地产），修改标题price inflation for all items since 1913":
        "Changed colors, extended inflation topic to broader price issues (real estate), title: 'price inflation for all items since 1913'.",
    "主图样式基本保留，整体加粗的轻微变化，但是呼应主题，保持冷静，稳重":
        "Main style preserved; slight bolding of elements echoing the theme, maintaining a calm, measured tone.",
    "通过颜色调整减轻对比，反向呼吁不要限制，有权让免疫系统自然地应对这个问题":
        "Softened color contrast to downplay severity, advocated against restrictions, framing natural immunity as the right approach.",
    "修改配色，修改图表类型，从线性变为面积图，增加视觉冲击":
        "Changed colors, changed chart type from line to area chart, increased visual impact.",
    "修改配色，增加对比变量大学应届毕业生的失业率":
        "Changed colors, added comparison variable: unemployment rate for recent college graduates.",
    "修改配色、增加注释、修改主题":
        "Changed colors, added annotations, modified title/theme.",
    "日均变月均，视觉增高":
        "Changed data granularity from daily to monthly averages, visually increasing bar height.",
    "增加拜登对比注释":
        "Added annotation comparing Biden administration data.",
    "增加驱逐的新数据系列":
        "Added new data series for deportation/expulsion numbers.",
    "通过改变标题说明这是不好的问题，然后通过调整注释，突出特朗普的政绩":
        "Changed title framing the issue negatively, adjusted annotations to highlight Trump administration achievements.",
    "添加不同种族出生率数据系列对比":
        "Added birth rate data series comparing different racial groups.",
    "添加其他总统时期数据对比":
        "Added data comparison across different presidential administrations.",
    "修改配色，修改背景，到TCN视频媒体平台获得更多传播":
        "Changed colors and background; redistributed on TCN video platform for wider reach.",
    "添加注释":
        "Added annotations.",
    "说疫情可能导致浓度下降":
        "Annotated that the pandemic may have caused a decrease in CO\u2082 concentration.",
    "修改配色，2022年将成为年平均CO2浓度首次超过工业化前水平50%的第一年":
        "Changed colors; annotated that 2022 would be the first year average CO\u2082 exceeds 50% above pre-industrial levels.",
    "增加标注（颜色突出）":
        "Added color-highlighted annotations.",
    "筛选数据变量呈现":
        "Filtered data variables for selective presentation.",
    "优秀案例。图表纵横比直接变化了":
        "Notable case: aspect ratio dramatically altered.",
    "变为由每年变为累积，变成面积图导致纵轴尺度也变了":
        "Changed from yearly to cumulative; switched to area chart, altering Y-axis scale.",
    "纵横比也变化了，缩小了纵轴尺度，简化横轴，add legend又一次强调了死亡率":
        "Aspect ratio changed; compressed Y-axis scale, simplified X-axis, added legend re-emphasizing death rate.",
    "纵横比也变化了，缩小了纵轴尺度，简化横轴，add 纵轴annotation":
        "Aspect ratio changed; compressed Y-axis scale, simplified X-axis, added Y-axis annotation.",
    "颜色变了，突出标题强调黑人和白人智商差异":
        "Colors changed; title emphasizes IQ difference between Black and White populations.",
    "通过增加注释，传播偏见":
        "Added extensive annotations propagating racial bias claims about IQ and economic outcomes.",
    "给出了拟合后的回归趋势线以及具体直线方程，原始统计型图表被解释化":
        "Added fitted regression trend line with equation; raw statistical chart became interpretive.",
    "增加了注释，缩短了时间年限（之前是1960到2020，现在只到2012），并且加了From FBI data 2012 prelimaniry estimate 的注释":
        "Added annotations, shortened time range (1960-2020 to 1960-2012), added note 'From FBI data 2012 preliminary estimate'.",
    "细化坐标轴并改变了颜色":
        "Refined axis detail and changed colors.",
    "按照年份统计经济衰退率，同时用阴影部分做了标注，最终给出了短时间的预测。给出了议题Don't Wait For Recessions To Sell Stocks":
        "Plotted recession probability by year with shaded annotations, added short-term forecast. Introduced topic: 'Don't Wait For Recessions To Sell Stocks'.",
    "改变了颜色，增加了注释，突出high probability of us recession":
        "Changed colors, added annotations highlighting 'high probability of US recession'.",
    "使用不同利差指标并以颜色区分预测信号，通过引入其他对比项延伸了议题":
        "Used different yield spread indicators color-coded as prediction signals, extending the topic with additional comparison variables.",
    "改变了颜色":
        "Changed colors.",
    "时间范围变化但未突出疫情冲击，整体框架保持":
        "Time range changed but did not highlight pandemic impact; overall framing preserved.",
    "图片本身未变，仅受平台历史数据限制":
        "Image unchanged; only limited by platform's historical data availability.",
    "与原图变化不大，仅语境化标题":
        "Minimal change from original; only contextualized the title.",
    "在关键时间点增加政策解释性注释":
        "Added policy-explanatory annotations at key time points.",
    "从原图截取并更新至最新年份，除了时间更新到最新的时间之外（只到2022）没有其他变化":
        "Cropped from original and updated to latest year (through 2022); no other changes.",
    "改变了颜色，增加了一条红色的（从2020开始暴涨有快速回跌的过程）下降的引导趋势线":
        "Changed colors; added a red trend line showing the spike-and-rapid-decline pattern starting from 2020.",
    "引入了俄亥俄州失业率，将美国（红色）与俄亥俄州失业率（蓝色）进行对比":
        "Introduced Ohio unemployment rate; compared US (red) vs. Ohio (blue) unemployment rates.",
    "仅在配色和说明层面调整，框架基本不变":
        "Only adjusted colors and labels; framing essentially unchanged.",
    "增加注释，在2010年后加入预测趋势并明确分界":
        "Added annotations; introduced post-2010 projected trend with clear demarcation.",
    "较N0(V1)修改了配色":
        "Changed color scheme compared to source.",
    "通过对关键数据点增加历史事件关联的注释和因果解读，拓展了议题The History of Voter Turnout in the US，同时通过改变背景为蓝色":
        "Added historical event annotations at key data points with causal interpretation, expanding topic to 'The History of Voter Turnout in the US'; changed background to blue.",
    "细化坐标轴的同时把每一年的数据在曲线上加重标注出来":
        "Refined axes while emphasizing each year's data point on the curve.",
    "ONS按周发布登记死亡人数，含完整数据来源、统计口径说明、区分和疫情有关的死亡数和无关的死亡数":
        "ONS publishes weekly death registrations with full data sources, statistical notes, distinguishing COVID-related and non-COVID deaths.",
    "指出covid deaths are rising, BBC调整了图表类型为面积图、更改了配色、增加标题疫情死亡上升的描述、更改图例名称deaths not involving covid-19变为official covid-19、简化了坐标轴":
        "Stated 'covid deaths are rising'; BBC changed chart to area chart, updated colors, added narrative title, renamed legend from 'deaths not involving covid-19' to 'official covid-19', simplified axes.",
    "更改了配色。简化了坐标轴。增加了注释（指出和正常相比死亡数的百分比）、通过使用灰色背景突出超额死亡部分、修改标题强化读者对\"疫情导致大量超额死亡\"":
        "Changed colors. Simplified axes. Added annotations (showing death percentage vs. normal), used grey background to highlight excess deaths, modified title to emphasize 'pandemic caused significant excess deaths'.",
    "NOAA定时更新全球温度情况":
        "NOAA regularly updates global temperature data.",
    "更改配色（强化），简化坐标轴，改变标题说world set for hottest july on record，增加注释warmer than average":
        "Intensified colors, simplified axes, changed title to 'world set for hottest July on record', added annotation 'warmer than average'.",
    "修改配色，增加新的变量：percent growth of U.S. healthcare spending per capita美国人均医疗保健支出增长的百分比":
        "Changed colors, added new variable: percent growth of U.S. healthcare spending per capita.",
    "引入历史关键事件议题增加注释，增加背景配图，改变标题美国通货膨胀的过去现在未来":
        "Introduced historical event annotations, added background image, changed title to 'US inflation: past, present and future'.",
    "拓展数据，发现下降改变标题说在去森林化率哪一年下降了，修改配色":
        "Extended data range, discovered decline, changed title highlighting the year deforestation rate dropped, changed colors.",
    "加粗注释，修改颜色":
        "Bolded annotations, changed colors.",
    "修改之前对比强烈的配色（让对比显得温和），改变注释":
        "Softened previously strong color contrasts (making comparisons appear mild), changed annotations.",
    "修改数据粒度":
        "Changed data granularity.",
    "修改配色，修改背景":
        "Changed colors and background.",
    "增加变量":
        "Added new data variables.",
    "增加注释":
        "Added annotations.",
    "增加注释（案例一般）":
        "Added annotations (moderate case).",
    "增加标记线引导":
        "Added guiding marker lines.",
    "说疫苗有害":
        "Claimed vaccines are harmful.",
    "变为由每年变为累积，变成面积图":
        "Changed from yearly to cumulative view, switched to area chart.",
    "质疑疫苗安全性与有效性：反复强调\"接种后刺突蛋白5个月仍在体内循环\"\"早期接种者感染率是后期2倍\"\"接种者病毒载量更高、更易传播\"等观点，引用VAERS死亡数据、辉瑞采购协议中\"长期效果未知\"的条款作为支撑":
        "Questioned vaccine safety and efficacy: repeatedly emphasized claims such as 'spike protein circulates 5 months post-vaccination', 'early vaccinees have 2x infection rate', 'vaccinated carry higher viral loads'. Cited VAERS death data and Pfizer purchase agreement clauses about 'unknown long-term effects'.",
    "现在有独立的数据来源可以验证COVID-19疫苗危险性的VAERS记录":
        "Claimed independent data sources now verify VAERS records showing COVID-19 vaccine dangers.",
    "通过修改标题、大写注释、增加y轴，改变配色":
        "Changed title, capitalized annotations, adjusted Y-axis, changed colors.",
    "根据今天早些时候发布的S&P CoreLogic Case-Shiller全国房价指数，全国房价同比上涨了6.3%（未进行季节性调整）。该指数现已超过2006年7月住房泡沫1的疯狂峰值，当时它开始以壮观的方式崩溃。得益于激进和实验性的货币政策，自住房崩盘1的低点以来，房价已重新膨胀了46%":
        "Based on S&P CoreLogic Case-Shiller index, national home prices rose 6.3% YoY (non-seasonally adjusted). The index now exceeds the July 2006 Housing Bubble 1 peak. Since the Housing Bust 1 trough, prices have re-inflated 46% thanks to aggressive and experimental monetary policies.",
    "按年份统计了近六十年来的暴力犯罪统计率":
        "Compiled nearly 60 years of violent crime rates by year.",
    "给出了拟合后的回归趋势线以及具体直线方程的数据":
        "Provided fitted regression trend line with specific linear equation.",
    "通过对关键数据点增加历史事件关联的注释，拓展了议题The History of Voter Turnout in the US，同时通过改变背景为蓝色":
        "Added historical event annotations at key data points, expanding topic to 'The History of Voter Turnout in the US'; changed background to blue.",
    "voter turnout，去掉了midterm数据系列，只保留presidential数据系列":
        "Voter turnout; removed midterm data series, kept only presidential series.",
    "更换了颜色":
        "Changed colors.",
    "fred网站标题为Smoothed U.S. Recession Probabilities (RECPROUSM156N)":
        "FRED website: Smoothed U.S. Recession Probabilities (RECPROUSM156N).",
    "引入了股票市场议题，按照年份统计经济衰退率，同时用阴影部分做了标注，最终给出了短时间的预测。给出了议题Don't Wait For Recessions To Sell Stocks":
        "Introduced stock market topic; plotted recession probability by year with shaded annotations and short-term forecast. Topic: 'Don't Wait For Recessions To Sell Stocks'.",
    "增加对比项，使用10年期-3个月期国债利差（蓝色）和10年期-2年期国债利差（红色）预测未来12个月的经济衰退概率，通过引入其他对比项延伸了议题":
        "Added comparison variables: 10yr-3mo Treasury spread (blue) and 10yr-2yr spread (red) for 12-month recession probability forecast, extending the topic.",
    "更改配色，增加注释":
        "Changed colors, added annotations.",
    "tradingeconomics上没有找到原图。但是多图来源指向此来源":
        "Original chart not found on TradingEconomics, but multiple variants trace back to this source.",
    "从1949-2021的12.01的美国居民劳动率，在2020有剧变下降":
        "US labor force participation rate from 1949-2021; dramatic drop in 2020.",
    "简化了坐标轴":
        "Simplified axes.",
    "在N0的基础上在1968左右的时间点加上注释，强调婴儿出生率快速上升提到了劳动参加率":
        "Added annotation around 1968 emphasizing rapid rise in baby boomer birth rates and its connection to labor force participation.",
    "近20年来的居民失业率":
        "Civilian unemployment rate over the past 20 years.",
    "除了时间更新到最新的时间之外（只到2022）没有其他变化":
        "No changes other than time range updated to 2022.",
    "柱状图展示2015-2022期间直接与间接的化石燃料补贴":
        "Bar chart showing direct and indirect fossil fuel subsidies from 2015-2022.",
    "1830年至2010年全球能源消耗趋势":
        "Global energy consumption trends from 1830 to 2010.",
    "增加了2010年之后的预测趋势，以2010为界限做分割做了标记":
        "Added post-2010 projected trend with clear 2010 demarcation.",
    "说疫情可能导致浓度下降":
        "Annotated that the pandemic may have caused CO\u2082 concentration decline.",
    "修改配色，2022年将成为年平均CO2浓度首次超过工业化前水平50%的第一年":
        "Changed colors; annotated 2022 as first year average CO\u2082 exceeds 50% above pre-industrial levels.",
    "西雅图对卖方不利，价格正在下跌":
        "Seattle unfavorable for sellers; prices declining.",
    "修改颜色，新增对比变量，其他主图样式基本保留":
        "Changed colors, added comparison variable (recent college graduate unemployment); main chart style mostly preserved.",
    "说浓度超过50%，但met office之前是说预测会下降":
        "Claimed concentration exceeded 50% above pre-industrial levels, contradicting Met Office's earlier prediction of a decline.",
    "增加大量注释，它进一步宣称，高薪工作需要\"最聪明的人\"，而由于IQ分布的差异，白人在高智商区间占比更高，因此他们在社会和经济上的优势是\"自然且合理\"的。传播偏见":
        "Added extensive annotations claiming high-paying jobs require 'the smartest people' and that due to IQ distribution differences, White people are overrepresented in higher IQ ranges, framing their socioeconomic advantages as 'natural and justified'. Propagated racial bias.",
    "缩短时间年限并增加解释性注释，突出特定阶段趋势":
        "Shortened time range and added explanatory annotations, highlighting trends in specific periods.",
    "只选择一个数据项系列展示，去掉了midterm数据系列，只保留presidential数据系列":
        "Selected only one data series: removed midterm elections, kept only presidential election turnout.",
    "更换了颜色，完整了图例描述从presidential变为presidential elections":
        "Changed colors; expanded legend description from 'presidential' to 'presidential elections'.",
    "调整配色":
        "Adjusted color scheme.",
}

NODE_LABEL_EN = {
    "英国统计机构ONS": "UK ONS (Office for National Statistics)",
    "V1: BBC转载": "V1: BBC Repost",
    "V2: 个人维护的新闻社区网站": "V2: Personal News Community Website",
    "V3: BBC转载": "V3: BBC Repost",
    "美国国家海洋和大气管理局NOAA": "US NOAA",
    "V1: Tweet用户Steve Molly": "V1: Twitter User Steve Molly",
    "美国国家健康计划项目PNHP": "US PNHP (Physicians for a National Health Program)",
    "V1: IBJ新闻媒体": "V1: IBJ News Media",
    "V2: Tweet用户Calley Means白宫议员": "V2: Twitter User Calley Means (White House Advisor)",
    "INPE巴西国家空间研究院": "INPE (Brazil National Institute for Space Research)",
    "V3: Mongabay环境保护新闻网站": "V3: Mongabay (Environmental News)",
    "V1: Advisor channel频道": "V1: Advisor Channel",
    "V3: 房地产社区": "V3: Real Estate Community Blog",
    "Reutres路透社": "Reuters",
    "V2: Inc新闻网站": "V2: Inc. News",
    "tweet发布政治图表的用户（粉丝多）": "Twitter User (Political Charts, Large Following)",
    "V1: 原创作者自行迭代": "V1: Original Author Self-Iteration",
    "V2: 原创作者自行迭代": "V2: Original Author Self-Iteration",
    "V2: 社区": "V2: Online Community",
    "V1: 英国气象局Met office": "V1: UK Met Office",
    "V2: World Economic Forum世界经济论坛": "V2: World Economic Forum",
    "V1: 普通用户": "V1: General User",
    "V2: 普通用户": "V2: General User",
    "V3: 普通用户": "V3: General User",
    "Swiss Policy Research (SPR)研究小组": "Swiss Policy Research (SPR)",
    "V2: Swiss Policy Research (SPR)研究小组": "V2: Swiss Policy Research (SPR)",
    "V3: 前身是Reddit子版块r/The_Donald，2020年因违反平台规则被封禁后，支持者迁至thedonald.win，后更名patriots.win":
        "V3: patriots.win (formerly r/The_Donald on Reddit, banned 2020)",
    "V4: 个人运营的网站": "V4: Privately Operated Website",
    "the bell curve书": "The Bell Curve (Book)",
    "V1: IFUNNY个人用户": "V1: iFunny User",
    "V2: 4chan论坛匿名用户": "V2: 4chan Anonymous User",
    "wolfstreet个人网站": "Wolf Street (Personal Website)",
    "V1: wolfstreet个人网站": "V1: Wolf Street",
    "V2: wolfstreet个人网站": "V2: Wolf Street",
    "美国公益性网站The Disaster Center": "The Disaster Center (US Public Interest Website)",
    "V2: imgur免费图片托管（图床）和分享社区": "V2: Imgur (Image Hosting Community)",
    "V3: Sean Williams佛罗里达大学教授": "V3: Prof. Sean Williams (Univ. of Florida)",
    "弗罗里达大学选举实验室": "Univ. of Florida Election Lab",
    "business insider媒体新闻网站（source是US Election Project）": "Business Insider (source: US Election Project)",
    "V2: historyinchart个人统计网站": "V2: History in Charts (Personal Stats Website)",
    "MarketWatch新闻媒体": "MarketWatch",
    "V1: visualcapitalist网站": "V1: Visual Capitalist",
    "tradingeconomics United States Department of Labor 美国劳工统计局":
        "TradingEconomics / US Dept. of Labor (BLS)",
    "V1: 普通用户": "V1: General User",
    "V2: University of Richmond Blogs大学论坛": "V2: Univ. of Richmond Blogs",
    "V3: linkedin普通用户": "V3: LinkedIn General User",
    "V4: utah.gov犹他州政府": "V4: Utah.gov (State Government)",
    "United States Department of Labor 美国劳工统计局": "US Dept. of Labor (BLS)",
    "V2: Mission Wealth经济组织": "V2: Mission Wealth",
    "V3: 维基百科": "V3: Wikipedia",
    "statista（source应该是International Monetary Fund，但是没有找到）":
        "Statista (source likely IMF, original not found)",
    "V1: eurasiareview新闻媒体网站": "V1: Eurasia Review",
    "resoilfoundation新闻网站": "Re Soil Foundation (News Website)",
    "V1: peakoil论坛": "V1: Peak Oil Forum",
    "V2: AAPG演讲 Cindy Yeilding": "V2: AAPG Presentation by Cindy Yeilding",
    "V2: NASA": "V2: NASA",
    "V3: BBC": "V3: BBC",
    "V2: zerohedge": "V2: ZeroHedge",
    "V3: Motley Fool": "V3: Motley Fool",
    "V3: econbrowser（Analysis of current economic conditions and policy）":
        "V3: Econbrowser",
    "V3: TCN": "V3: TCN",
    "V1: Climate Depot": "V1: Climate Depot",
    "newyork news": "New York Times",
    "V1: JFP news": "V1: JFP News",
    "V2: Armstrong economics": "V2: Armstrong Economics",
    "V1: Ycharts": "V1: YCharts",
    "V1: Senator Ron Johnson's office": "V1: Sen. Ron Johnson's Office",
    "V2: Senator Ron Johnson's office": "V2: Sen. Ron Johnson's Office",
    "V3: Senator Ron Johnson's office": "V3: Sen. Ron Johnson's Office",
    "V4: Senator Ron Johnson's office": "V4: Sen. Ron Johnson's Office",
    "V5: Trump team": "V5: Trump Campaign Team",
    "V1: the automatic earth": "V1: The Automatic Earth",
    "V2: finance.yahoo": "V2: Yahoo Finance",
    "CBP public data dashboard": "CBP Public Data Dashboard",
}

# ── parse markdown tables ──────────────────────────────────────

def parse_md_table(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows, header = [], None
    for line in lines:
        line = line.strip()
        if not line.startswith("|") or line.startswith("||"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if header is None:
            header = cells
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(dict(zip(header, cells)))
    return rows

# ── remap C21-C27 → C16-C22 ────────────────────────────────────

REMAP = {"C21": "C16", "C22": "C17", "C23": "C18", "C24": "C19",
         "C25": "C20", "C26": "C21", "C27": "C22"}

def remap_id(raw: str) -> str:
    """Remap case/node/edge IDs: C21-N0 → C16-N0, C21-E1 → C16-E1, etc."""
    for old, new in REMAP.items():
        if raw.startswith(old):
            return new + raw[len(old):]
    return raw

# ── load taxonomy ──────────────────────────────────────────────

cases_raw = parse_md_table(TAX / "taxonomy_case.md")
nodes_raw = parse_md_table(TAX / "taxonomy_who_where.md")
edges_raw = parse_md_table(TAX / "taxonomy_how.md")

def translate(text: str, table: dict) -> str:
    return table.get(text.strip(), text)

cases = OrderedDict()
for r in cases_raw:
    cid = remap_id(r["case_id"])
    raw_vt = r.get("viz_type", "")
    cases[cid] = {
        "case_id": cid,
        "topic": TOPIC_EN.get(cid, r.get("topic", "")),
        "viz_type": VIZ_TYPE_EN.get(raw_vt, raw_vt),
        "source_medium": r.get("source_medium", ""),
        "total_variants": int(r.get("total_variants", 0)),
        "max_depth": int(r.get("max_depth", 0)),
        "topology_type": r.get("topology_type", ""),
        "category": translate(r.get("notes", ""), CATEGORY_EN),
        "nodes": [],
        "edges": [],
    }

for r in nodes_raw:
    cid = remap_id(r.get("case_id", ""))
    if cid not in cases:
        continue
    role = r.get("role", "").strip().lower()
    if "/" in role:
        role = role.split("/")[-1]
    raw_desc = r.get("content_description", "")
    raw_label = r.get("node_label", "")
    cases[cid]["nodes"].append({
        "node_id": remap_id(r.get("node_id", "")),
        "is_source": r.get("is_source", "no").strip().lower() == "yes",
        "label": NODE_LABEL_EN.get(raw_label, raw_label),
        "role": role,
        "platform": PLAT_EN.get(r.get("platform", ""), r.get("platform", "")),
        "platform_en": PLAT_EN.get(r.get("platform", ""), r.get("platform", "")),
        "description": EVIDENCE_EN.get(raw_desc, raw_desc),
    })

def norm_ops(raw: str) -> list[dict]:
    ops = []
    for o in re.split(r",\s*", raw.strip()):
        o = o.strip().lower()
        if not o:
            continue
        l1 = OP_L1.get(o, "Textual Elements")
        ops.append({"op": o, "l1": l1})
    return ops

for r in edges_raw:
    cid = remap_id(r.get("case_id", ""))
    if cid not in cases:
        continue
    raw_ev = r.get("evidence_description", "")
    cases[cid]["edges"].append({
        "edge_id": remap_id(r.get("edge_id", "")),
        "source_node": remap_id(r.get("source_node", "")),
        "target_node": remap_id(r.get("target_node", "")),
        "source_role": r.get("source_role", "").strip().lower(),
        "target_role": r.get("target_role", "").strip().lower(),
        "source_platform": PLAT_EN.get(r.get("source_institution", ""), r.get("source_institution", "")),
        "target_platform": PLAT_EN.get(r.get("target_institution", ""), r.get("target_institution", "")),
        "operations": norm_ops(r.get("frame_operation", "")),
        "shift_magnitude": r.get("shift_magnitude", ""),
        "evidence": EVIDENCE_EN.get(raw_ev, raw_ev),
    })

# ── scan images ────────────────────────────────────────────────

def load_image_b64(case_id: str) -> str | None:
    rel = CASE_IMAGE_MAP.get(case_id)
    if not rel:
        return None
    d = ROOT / rel
    for name in ["ori_image.png", "visualization.svg", "chart_preview.png"]:
        p = d / name
        if p.exists():
            data = p.read_bytes()
            mime = "image/png" if p.suffix == ".png" else "image/svg+xml"
            return f"data:{mime};base64,{base64.b64encode(data).decode()}"
    return None

images = {}
for cid in cases:
    img = load_image_b64(cid)
    if img:
        images[cid] = img

print(f"Loaded {len(cases)} cases, images for {len(images)} cases")

# ── write corpus.json ──────────────────────────────────────────

corpus_data = list(cases.values())
(OUT / "corpus.json").write_text(
    json.dumps(corpus_data, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"Saved corpus.json ({len(corpus_data)} cases)")

# ── stats ──────────────────────────────────────────────────────

total_nodes = sum(len(c["nodes"]) for c in corpus_data)
total_edges = sum(len(c["edges"]) for c in corpus_data)
role_counts: dict[str, int] = {}
op_l1_counts: dict[str, int] = {}
mag_counts: dict[str, int] = {}
for c in corpus_data:
    for n in c["nodes"]:
        role_counts[n["role"]] = role_counts.get(n["role"], 0) + 1
    for e in c["edges"]:
        mag = e["shift_magnitude"]
        mag_counts[mag] = mag_counts.get(mag, 0) + 1
        for op in e["operations"]:
            op_l1_counts[op["l1"]] = op_l1_counts.get(op["l1"], 0) + 1

# ── build HTML ─────────────────────────────────────────────────

def role_badge(role: str) -> str:
    c = ROLE_COLOR.get(role, "#888")
    return f'<span class="badge" style="background:{c}">{role.title()}</span>'

def plat_badge(plat_zh: str) -> str:
    en = PLAT_EN.get(plat_zh, plat_zh)
    return f'<span class="badge plat">{en}</span>'

def op_pill(op: dict) -> str:
    c = L1_COLOR.get(op["l1"], "#888")
    return f'<span class="op-pill" style="border-color:{c};color:{c}">{op["op"]}</span>'

def mag_dot(mag: str) -> str:
    colors = {"none": "#ccc", "minor": "#6AAA3A", "significant": "#D08350", "major": "#C44E42"}
    c = colors.get(mag, "#888")
    return f'<span class="mag-dot" style="background:{c}" title="{mag}"></span> {mag}'

def build_case_card(c: dict) -> str:
    cid = c["case_id"]
    n_nodes = len(c["nodes"])
    n_edges = len(c["edges"])
    roles_set = sorted(set(n["role"] for n in c["nodes"]))
    roles_html = " ".join(role_badge(r) for r in roles_set)

    # nodes table
    nodes_rows = ""
    for n in c["nodes"]:
        src = "&#9733;" if n["is_source"] else ""
        nodes_rows += f"""<tr>
            <td><code>{n['node_id']}</code></td>
            <td>{src}</td>
            <td>{role_badge(n['role'])}</td>
            <td>{plat_badge(n['platform'])}</td>
            <td class="label-cell">{n['label']}</td>
            <td class="desc-cell">{n['description']}</td>
        </tr>"""

    # edges table
    edges_rows = ""
    for e in c["edges"]:
        ops_html = " ".join(op_pill(o) for o in e["operations"])
        edges_rows += f"""<tr>
            <td><code>{e['source_node']}</code> &rarr; <code>{e['target_node']}</code></td>
            <td>{role_badge(e['source_role'])} &rarr; {role_badge(e['target_role'])}</td>
            <td>{ops_html}</td>
            <td>{mag_dot(e['shift_magnitude'])}</td>
            <td class="desc-cell">{e['evidence']}</td>
        </tr>"""

    # image
    img_html = ""
    if cid in images:
        img_html = f'<div class="case-img"><img src="{images[cid]}" alt="Source visualization for {cid}"><p class="img-cap">Source Visualization</p></div>'

    return f"""
    <details class="case-card" data-roles="{','.join(roles_set)}" data-category="{c['category']}">
        <summary>
            <span class="cid">{cid}</span>
            <span class="topic">{c['topic']}</span>
            <span class="meta">{c['viz_type']} &middot; {n_nodes} nodes &middot; {n_edges} edges &middot; depth {c['max_depth']} &middot; {c['topology_type']}</span>
            {roles_html}
        </summary>
        <div class="card-body">
            <div class="case-header-row">
                <div class="case-meta">
                    <p><strong>Source:</strong> {c['source_medium']}</p>
                    <p><strong>Category:</strong> {c['category']}</p>
                </div>
                {img_html}
            </div>
            <h4>Nodes ({n_nodes})</h4>
            <table class="tbl"><thead><tr>
                <th>ID</th><th>Src</th><th>Role</th><th>Platform</th><th>Label</th><th>Description</th>
            </tr></thead><tbody>{nodes_rows}</tbody></table>
            <h4>Edges ({n_edges})</h4>
            <table class="tbl"><thead><tr>
                <th>Link</th><th>Roles</th><th>Operations</th><th>Shift</th><th>Evidence</th>
            </tr></thead><tbody>{edges_rows}</tbody></table>
        </div>
    </details>"""

cards_html = "\n".join(build_case_card(c) for c in corpus_data)

# stats bars
def stat_bar(label: str, count: int, total: int, color: str) -> str:
    pct = count / total * 100 if total else 0
    return f'<div class="stat-row"><span class="stat-label">{label}</span><div class="stat-bar-bg"><div class="stat-bar" style="width:{pct:.1f}%;background:{color}"></div></div><span class="stat-val">{count}</span></div>'

role_bars = "\n".join(stat_bar(r.title(), role_counts.get(r, 0), total_nodes, ROLE_COLOR.get(r, "#888"))
                      for r in ["bridger", "amplifier", "extender", "adverser"])
op_bars = "\n".join(stat_bar(k, v, sum(op_l1_counts.values()), L1_COLOR.get(k, "#888"))
                    for k, v in sorted(op_l1_counts.items()))

all_categories = sorted(set(c["category"] for c in corpus_data if c["category"]))
cat_options = "\n".join(f'<option value="{cat}">{cat}</option>' for cat in all_categories)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Corpus: Visualization Framing Shifts</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#f7f8fa;color:#333;line-height:1.6}}
.container{{max-width:1200px;margin:0 auto;padding:24px}}
header{{text-align:center;padding:32px 0 16px}}
header h1{{font-size:1.8rem;color:#2c3e50;margin-bottom:8px}}
header p{{color:#666;font-size:0.95rem}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}}
.stat-card{{background:#fff;border-radius:8px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.stat-card .num{{font-size:1.8rem;font-weight:700;color:#2c3e50}}
.stat-card .lbl{{font-size:.8rem;color:#888;text-transform:uppercase;letter-spacing:.5px}}
.section{{background:#fff;border-radius:8px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.section h3{{font-size:1rem;color:#555;margin-bottom:12px;border-bottom:1px solid #eee;padding-bottom:8px}}
.stat-row{{display:flex;align-items:center;gap:8px;margin:4px 0}}
.stat-label{{width:140px;font-size:.85rem;text-align:right}}
.stat-bar-bg{{flex:1;height:18px;background:#f0f0f0;border-radius:9px;overflow:hidden}}
.stat-bar{{height:100%;border-radius:9px;transition:width .3s}}
.stat-val{{width:36px;font-size:.8rem;color:#666;text-align:right}}
.filters{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:16px 0}}
.filters label{{font-size:.85rem;color:#666}}
.filters select,.filters input{{padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:.85rem}}
.filters input{{flex:1;min-width:200px}}
.case-card{{background:#fff;border-radius:8px;margin:8px 0;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden}}
.case-card summary{{display:flex;align-items:center;gap:10px;padding:12px 16px;cursor:pointer;flex-wrap:wrap}}
.case-card summary:hover{{background:#f9fafe}}
.case-card[open] summary{{border-bottom:1px solid #eee;background:#f9fafe}}
.cid{{font-weight:700;color:#2c3e50;min-width:36px;font-size:.9rem}}
.topic{{font-weight:600;color:#444;min-width:160px;font-size:.9rem}}
.meta{{color:#999;font-size:.78rem}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-size:.72rem;font-weight:600;text-transform:capitalize}}
.badge.plat{{background:#f0f0f0;color:#555;border:1px solid #ddd}}
.op-pill{{display:inline-block;padding:1px 7px;border:1.5px solid;border-radius:10px;font-size:.72rem;font-weight:500;margin:1px}}
.mag-dot{{display:inline-block;width:10px;height:10px;border-radius:50%}}
.card-body{{padding:16px}}
.card-body h4{{font-size:.9rem;color:#555;margin:16px 0 8px;border-bottom:1px solid #f0f0f0;padding-bottom:4px}}
.card-body h4:first-child{{margin-top:0}}
.case-header-row{{display:flex;gap:20px;align-items:flex-start}}
.case-meta{{flex:1}}
.case-meta p{{font-size:.85rem;margin:4px 0}}
.case-img{{max-width:280px;flex-shrink:0}}
.case-img img{{max-width:100%;border:1px solid #eee;border-radius:6px}}
.img-cap{{font-size:.75rem;color:#999;text-align:center;margin-top:4px}}
.tbl{{width:100%;border-collapse:collapse;font-size:.8rem}}
.tbl th{{background:#f7f8fa;padding:6px 8px;text-align:left;font-weight:600;color:#555;border-bottom:2px solid #eee}}
.tbl td{{padding:6px 8px;border-bottom:1px solid #f0f0f0;vertical-align:top}}
.desc-cell{{max-width:320px;font-size:.78rem;color:#666}}
.label-cell{{max-width:200px}}
footer{{text-align:center;padding:32px 0;color:#aaa;font-size:.8rem}}
.hidden{{display:none!important}}
</style>
</head>
<body>
<div class="container">
<header>
    <h1>Corpus of Visualization Framing Shifts</h1>
    <p>{len(cases)} cases &middot; {total_nodes} nodes &middot; {total_edges} edges &middot;
       covering {len(all_categories)} topic categories</p>
</header>

<div class="stats-grid">
    <div class="stat-card"><div class="num">{len(cases)}</div><div class="lbl">Cases</div></div>
    <div class="stat-card"><div class="num">{total_nodes}</div><div class="lbl">Nodes</div></div>
    <div class="stat-card"><div class="num">{total_edges}</div><div class="lbl">Edges</div></div>
    <div class="stat-card"><div class="num">{sum(op_l1_counts.values())}</div><div class="lbl">Operations</div></div>
</div>

<div class="section">
    <h3>Role Distribution</h3>
    {role_bars}
</div>
<div class="section">
    <h3>Operation Categories</h3>
    {op_bars}
</div>

<div class="filters">
    <label>Filter:</label>
    <select id="fRole"><option value="">All Roles</option>
        <option value="bridger">Bridger</option><option value="amplifier">Amplifier</option>
        <option value="extender">Extender</option><option value="adverser">Adverser</option>
    </select>
    <select id="fCat"><option value="">All Categories</option>{cat_options}</select>
    <input type="text" id="fSearch" placeholder="Search topic or case ID...">
    <button onclick="document.querySelectorAll('details.case-card').forEach(d=>d.open=true)">Expand All</button>
    <button onclick="document.querySelectorAll('details.case-card').forEach(d=>d.open=false)">Collapse All</button>
</div>

<div id="caseList">
{cards_html}
</div>

<footer>
    Generated from taxonomy data &middot; {len(cases)} cases
    &middot; <a href="corpus.json" download>Download corpus.json</a>
</footer>
</div>

<script>
const fRole=document.getElementById('fRole'),
      fCat=document.getElementById('fCat'),
      fSearch=document.getElementById('fSearch');
function applyFilters(){{
    const role=fRole.value, cat=fCat.value, q=fSearch.value.toLowerCase();
    document.querySelectorAll('.case-card').forEach(card=>{{
        const roles=card.dataset.roles||'', category=card.dataset.category||'',
              text=card.querySelector('summary').textContent.toLowerCase();
        let show=true;
        if(role && !roles.includes(role)) show=false;
        if(cat && category!==cat) show=false;
        if(q && !text.includes(q)) show=false;
        card.classList.toggle('hidden',!show);
    }});
}}
fRole.onchange=fCat.onchange=fSearch.oninput=applyFilters;
</script>
</body>
</html>"""

(OUT / "corpus_browser.html").write_text(html, encoding="utf-8")
print(f"Saved corpus_browser.html")
print("Done!")
