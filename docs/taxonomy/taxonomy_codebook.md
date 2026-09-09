# 编码指南 / Codebook

## 角色类型 Role Type

| 编码值 | 理论来源 | 定义 / 编码说明 |
|--------|----------|----------------|
| bridger | Frame Alignment Processes, Micromobilization, and Movement Participation | **核心功能：连接数据与公众，建立信息传播的基础链路。** Bridger是数据可视化传播链条中的"源头角色"，主要由政府机构、官方组织、科研机构或第三方数据平台担任。其核心任务是将原始数据以相对客观、完整的方式公开呈现给公众，建立数据与受众之间的结构性连接。典型特征：配色相对客观、数据完整、有数据来源，以信息告知为主要目的，而非说服或动员。**语料库例子：** ONS发布死亡登记数据、NOAA更新全球温度数据、科研机构发布疫苗相关研究数据等。 |
| extender | | **核心功能：将原有议题延伸至更广泛的关联领域，扩展框架的解释范围。** Extender在保留原始数据的基础上，通过引入新变量、新维度或关联议题，将讨论从单一问题扩展到更宏观的社会、经济或政治语境中。其目的是增加议题的关联性和动员潜力，吸引原本对核心议题不敏感的受众群体。**典型操作手法：** 增加变量数据系列（如在通胀率图上叠加医疗支出增长率）；修改标题扩展议题（将"疫情死亡上升"延伸为"疫情如何影响超额死亡率"）；增加注释扩展议题（引入历史关键事件作为参照系）；时间线拓展（延展数据时间范围以建立历史纵深感）。**语料库例子：** 从US inflation rate延伸到price inflation for all items；在失业率图中增加大学毕业生失业率对比；在通胀数据中标注历史关键事件等。 |
| adverser | | **核心功能：构建与主流叙事相对立的解读框架，挑战既有共识。** Adverser通过选择性呈现数据、重新框定因果关系或直接否定主流解读，构建与官方或主流媒体叙事相矛盾的替代性框架。其目的可能是政治动员、阴谋论传播，或对主流叙事的正当质疑。**典型操作手法：** 截取数据范围（选取特定时间段数据支持相反结论，如截取降温周期数据声称"全球变冷"）；来源删除（移除原始数据出处，削弱可追溯性和可信度检验）；修改配色（将原本强烈的对比色调改为温和配色，淡化问题严重性）。**语料库例子：** 社交媒体截取NOAA数据的特定时段声称全球变冷；个人博客修改配色弱化数据对比强度。 |
| amplifier | | **核心功能：强化既有叙事框架，提升特定议题的显著性与情感冲击力。** Amplifier在不改变核心议题的前提下，对原始数据进行"信号增强"，使特定解读更加突出、鲜明、易于感知。其目的是让受众更强烈地认同某一框架。**典型操作手法：** 修改配色（使用高对比度、情感暗示性强的颜色方案）；坐标轴简化（删除冗余信息，聚焦核心数据）；修改标题（使用主题明确的标题，如"deaths are rising"）；添加注释（添加指向性注释，引导读者解读方向）；修改注释（通过颜色、加粗、大写突出注释，标注关键数据点）；纵横比调整（通过拉伸/压缩图表比例放大变化幅度）；坐标轴尺度调整（通过拉伸/压缩坐标轴比例放大变化幅度）；时间截取（选取特定时段数据以强化趋势感知）；增加背景（通过增加主题对应背景引发观众情感共鸣）。**语料库例子：** BBC将面积图配色改为更醒目的方案、新闻媒体截取2006年后数据强调森林砍伐率上升、社交媒体用大写字母和醒目颜色标注关键数据点等。 |

## 平台 Platform

| 编码值 | 说明 |
|--------|------|
| 第三方数据平台 | wikipedia、ycharts等 |
| 个人网站/博客 | 个人运营的网站、博客 |
| 科研机构 | 书、学术文献、选举实验室等 |
| 在线社区/UGC平台 | 各种论坛 |
| 社交媒体 | twitter、youtube |
| 新闻媒体 | BBC、JFP等新闻媒体 |
| 政府/官方机构/国际组织 | 政府、官方数据发布来源、世界经济论坛 |
| 机构博客 | 企业、机构运营的博客网站 |

## 框架操作 Frame Operation

| 编码值 | 类别 | 定义 |
|--------|------|------|
| select data variables | data | 筛选呈现的数据系列 |
| add data variables | data | 增加呈现的数据系列 |
| select time range | data | 选择时间范围 |
| change data granularity | data | 修改数据呈现粒度，比如日均变月均 |
| change type | visual | 改变图表类型 |
| change color | visual | 改变图表颜色 |
| add background | visual | 给图表增加背景 |
| simplify axis | visual | 简化坐标轴（以突出其他信息） |
| change aspect ratio | visual | 改变图片纵横比 |
| change axis scale | visual | 改变坐标轴尺度（比如缩小纵轴尺度以拉高） |
| change title | text | 改变标题 |
| add annotation | text | 增加注释 |
| change annotation | text | 改变注释 |
| delete source | text | 删除数据来源 |
| change legend | text | 改变图例描述 |
| add legend | text | 增加图例描述，以进一步重复强化 |

###典型例子：
select data variables（很少）：筛选呈现的数据系列，常作用于减少显示现有的数据系列项
例子：（bridger 个人网站/博客）主标题：US 20-city case-shiller house price index change from year ago ->（bridger 个人网站/博客）Seattle house price index

add data variables(extender倾向使用这个框架操作,难度较大，缺乏数据暂缓设计)：增加呈现的数据系列，作用于增加与原数据主题相关的数据

例子：(bridger 政府/官方机构/国际组织)主标题：Unemployment Rates -> (extender 新闻媒体) Unemployment Rates by different measures
分析：(extender 新闻媒体)倾向于**拓展 + 深化**拓展信息内涵、深化议题讨论,加入了recent graduates 对比变量
例子：(bridger 政府/官方机构/国际组织)Smoothed U.S. Recession Probabilities ->(extender 个人网站) 12 month ahead estimated probability of recession using 10yr-3mo Treasury spread (blue), 10yr-3mo spread and fed funds minus ex post lagged inflation (light blue), and using 10yr-2yr spread (red). NBER defined recession dates peak-to-trough shaded gray. Source: Treasury via FRED, NBER and author’s calculations.
分析：引入其他对比项延伸了议题12 month ahead estimated probability of recession using 10yr-3mo Treasury spread (blue), and using 10yr-2yr spread (red)

select time range：选择时间范围，常作用于横坐标数据
例子：(bridger 政府/官方机构/国际组织)主标题：Global Land and Ocean Average Temperature Anomaly ->(adverser 社交媒体) Global Cooling
分析：adverser筛选特定时间段的下降趋势的数据，得出和原始全量数据上升趋势（全球变暖）相反的结论（全球变冷）,并配趋势线注释说明
例子：(bridger 政府/官方机构/国际组织)主标题：Deforestation Rates-Legal Amazon-States ->(amplifier 新闻媒体)Amozon deforestation highest since 2006 
分析：amplifier 筛选2006年后特定时间段的数据，加强论证修改后的标题


change data granularity（较少例子）:修改数据呈现粒度，比如日均变月均，拉高纵向高度，也可以是月均变日均，降低纵向高度，根据角色、平台意图来定
例子：(amplifier 社交媒体)->(amplifier 社交媒体)
分析：将日均统计的数据合并为月均，增加纵向高度。


change type: 修改图表类型，比如柱状图变面积图，常作用于图表类型。
例子：堆叠柱状图(bridger 政府/官方机构/国际组织)->堆叠面积图(amplifier 新闻媒体) 
分析：(bridger 政府/官方机构/国际组织)倾向数据的准确性，堆叠柱状图数据显示准确;(amplifier 新闻媒体)倾向强化叙事，采用堆叠面积图适合展示总量趋势。

change color:修改图表配色，当所属平台、角色发生变化时，容易出现配色变化。bridger配色较为温和中立，amplifier倾向于强化配色对比，放大情绪，adverser倾向于使用和上一节点相反的配色，extender倾向于沿用上一节点的配色。
(bridger 政府/官方机构/国际组织)->(amplifier 新闻媒体) 新闻媒体倾向使用自己的配色

add background:增加图表背景
例子：(bridger政府/官方机构/国际组织)->(amplifier 新闻媒体)  Rate of deforestation in Amazon
分析：(amplifier 新闻媒体)在图表背景加了一个主题相关的配图-亚马逊森林的配图
例子：(bridger政府/官方机构/国际组织)->(extender 新闻媒体)在关键数据旁引入历史关键事件，并配相关的图


simplify axis:简化横坐标轴显示的值，常用于新闻媒体、amplifier、adverser以突出其他内容，比如标题、annotation;bridger一般不执行这个操作
例子：(bridger政府/官方机构/国际组织)横坐标每一年都列出来2000、2001、2002、2003...2020->(amplifier 新闻媒体) 将横坐标轴每年的值简化为每5年或每10年的列,比如2000、2005、2010、2015、2020


change aspect ratio:改变图片纵横比，一般出现在amplifier的个人网站、博客、社交媒体、在线社区/UGC平台。效果可能是拉高纵横比以放大值

change axis scale: 改变纵坐标轴尺度（比如从0-100变为50-100，缩小纵轴尺度以放大y值或者使得差异变明显）,可能出现的平台是amplifier的个人网站、博客、社交媒体、在线社区/UGC平台。



change title:改变标题，bridger一般不执行这个操作，amplifier 、adverser、extender都会执行这个操作，他们需要结合数据寻找适合自身叙事主题意图的title.特别的是adverser的操作是与完整图表显示的叙事相反的叙事意图.与此同时会在具体数据点附近加上简短美观的注释add annotation呼应自己的title.
例子：(bridger 政府/官方机构/国际组织)主标题：Deaths not involving COVID-19 remained below the five-year average in Week 47 副标题：Number of deaths registered by week, England and Wales, 28 December 2019 to 20 November 2020 -> (amplifier 新闻媒体)主标题Covid deaths are rising 副标题Weekly UK death registrations  -> (extender 新闻媒体)主标题how the pandemic has affected excess deaths 副标题Weekly UK death registrations
分析：(bridger 政府/官方机构/国际组织)倾向于**客观介绍数据**; (amplifier 新闻媒体)倾向于**收窄 + 放大**，强化叙事，描述趋势显现;(extender 新闻媒体)倾向于**拓展 + 深化**拓展信息内涵、深化议题讨论,把话题从 “新冠死亡” 扩展到 “疫情对超额死亡的影响”.
例子：(bridger 政府/官方机构/国际组织)主标题：Global Land and Ocean Average Temperature Anomaly ->  (amplifier 新闻媒体)主标题world set for hottest july on record
分析：(amplifier 新闻媒体)倾向于**收窄+放大**，强化叙事，描述极值
例子：(bridger 政府/官方机构/国际组织)主标题：Deforestation Rates-Legal Amazon-States ->(amplifier 新闻媒体)Amozon deforestation highest since 2006 
(bridger 政府/官方机构/国际组织)主标题：Deforestation Rates-Legal Amazon-States ->(amplifier 新闻媒体)Rate of deforestation fell in 2023
分析：(amplifier 新闻媒体)倾向于**收窄+放大**，强化叙事，描述趋势
例子：(bridger 政府/官方机构/国际组织)主标题：Unemployment Rates -> (extender 新闻媒体) Unemployment Rates by different measures
分析：(extender 新闻媒体)倾向于**拓展 + 深化**拓展信息内涵、深化议题讨论,加入了recent graduates 对比变量


add annotation:增加注释，希望是简短明了完整，不要出现省略号、呼应title和角色立场的，不要出现broader context这种宽泛的注释，而应该具体，结合你想强调的地方具体一些，每次add annotation前也需要考虑是否要删除之前存在的annotation，避免冲突矛盾。可以考虑两种方式，一种是只在对应地方附近增加文本说明，比如当标题强调趋势上升，可以在最高点加上具体数据注释。另一种是增加文本说明的同时，加上标注线/趋势线,比如想强调上升趋势时，在上升的时间范围中画一个趋势线。这是最常出现的框架修改操作，有可能出现在每种角色中，根据角色本身意图和对数据的理解和主题决定怎么增加annotation。比如extender引入历史关键事件议题增加注释说明数据增长或下降的原因，amplifier在对应数据附近增加注释以呼应强化当前title叙事，adverser发现对立叙事的可能，在对应数据附近增加注释、趋势线以对立叙事。

change annotation:修改注释，常出现amplifier中,比如将原有的注释变粗体，变字母大写，size变大，以强调强化。

delete source:删除数据来源，常出现在adverser、amplifier的社交媒体平台

add lgd:当源可视化没有legend时，amplifier为了强调可以补充legend，就当重复主题了。建议只能横着加在图表中或者上方。
例子：(bridger 科研机构) 标题All deaths reported to VAERS by year  ->(amplifier 在线社区/UGC平台) 标题All deaths reported to VAERS by year，标题下方增加了y轴数据系列的legend：Reports of deaths.这样通过增加legend重复了死亡率。
例子：(bridger 政府/官方机构/国际组织) mideterm、presidential->（bridger 第三方数据平台） mideterm elections。完整了图例描述从presidential变为presidential elections

change lgd: 修改之前的legend的命名，以突出主题，比如(bridger 政府/官方机构/国际组织)更改图例名称deaths not involving covid-19变为(amplifier 新闻媒体)official covid-19。

