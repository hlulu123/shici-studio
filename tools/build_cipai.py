"""Build shici-studio/assets/cipai.json.

句读、韵位由下面的 SPEC 手写（依龙榆生《唐宋词格律》一系的通行正体）；每个位置的平仄则用全宋词
同调、同字数的作品统计得出，SPEC 里的平仄只在样本不足或统计不明确时兜底。

    python3 -I tools/build_cipai.py <ci.db> <skill_dir> [-v]
"""
import collections
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shici-studio", "scripts"))
import shici_data as D  # noqa: E402

HAN = D.HAN_RE


def P(*segs):
    return list(segs)


def same(*segs):
    return [list(segs), list(segs)]


SPEC = {
    "忆江南": dict(alias=["望江南", "梦江南", "江南好"], mood="清丽明快，宜写景怀旧", example="白居易「江南好」",
                forms=[dict(name="单调", rhymes={"a": "平"}, parts=[P("中平仄，", "中仄仄平平a。", "中仄中平平仄仄，", "中平中仄仄平平a。", "中仄仄平平a。")]),
                       dict(name="双调", rhymes={"a": "平"}, parts=same("中平仄，", "中仄仄平平a。", "中仄中平平仄仄，", "中平中仄仄平平a。", "中仄仄平平a。"))]),
    "如梦令": dict(alias=["忆仙姿", "宴桃源"], mood="轻灵婉转，宜写小景小情", example="李清照「昨夜雨疏风骤」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=[P("中仄中平中仄a。", "中仄中平中仄a。", "中仄仄平平，", "中仄中平中仄a。", "平仄a，", "平仄a。", "中仄中平中仄a。")])]),
    "长相思": dict(alias=["双红豆", "忆多娇"], mood="回环往复，宜相思离情", example="白居易「汴水流」",
                forms=[dict(name="正体", rhymes={"a": "平"}, parts=same("中中平a，", "中中平a。", "中仄平平中仄平a，", "中平中仄平a。"))]),
    "相见欢": dict(alias=["乌夜啼", "秋夜月", "上西楼"], mood="平仄换韵，凄婉，宜离愁", example="李煜「无言独上西楼」",
                forms=[dict(name="正体", rhymes={"a": "平", "b": "仄"},
                            parts=[P("中平中仄平平a，", "中平平a。", "中仄中平中仄仄平平a。"),
                                   P("中仄仄b，", "中平仄b，", "仄平平a。", "中仄中平中仄仄平平a。")])]),
    "浣溪沙": dict(alias=["浣纱溪", "小庭花"], mood="明快婉丽，用途极广", example="晏殊「一曲新词酒一杯」",
                forms=[dict(name="正体", rhymes={"a": "平"},
                            parts=[P("中仄中平中仄平a，", "中平中仄仄平平a。", "中平中仄仄平平a。"),
                                   P("中仄中平平仄仄，", "中平中仄仄平平a。", "中平中仄仄平平a。")])]),
    "菩萨蛮": dict(alias=["子夜歌", "重叠金"], mood="平仄四换韵，情致缠绵", example="温庭筠「小山重叠金明灭」、李白（传）「平林漠漠烟如织」",
                forms=[dict(name="正体", rhymes={"a": "仄", "b": "平", "c": "仄", "d": "平"},
                            parts=[P("中平中仄平平仄a，", "中平中仄平平仄a。", "中仄仄平平b，", "中平中仄平b。"),
                                   P("中平平仄仄c，", "中仄平平仄c。", "中仄仄平平d，", "中平中仄平d。")])]),
    "采桑子": dict(alias=["丑奴儿", "罗敷媚"], mood="平和舒缓，宜写景抒怀", example="欧阳修「群芳过后西湖好」",
                forms=[dict(name="正体", rhymes={"a": "平"}, parts=same("中平中仄平平仄，", "中仄平平a。", "中仄平平a，", "中仄平平中仄平a。"))]),
    "卜算子": dict(alias=["百尺楼", "缺月挂疏桐"], mood="清峭，宜咏物言志", example="苏轼「缺月挂疏桐」、陆游「驿外断桥边」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=same("中仄仄平平，", "中仄平平仄a。", "中仄平平仄仄平，", "中仄平平仄a。"))]),
    "减字木兰花": dict(alias=["减兰", "木兰香"], mood="平仄四换韵，轻快", example="李清照「卖花担上」",
                  forms=[dict(name="正体", rhymes={"a": "仄", "b": "平", "c": "仄", "d": "平"},
                              parts=[P("中平中仄a，", "中仄中平平仄仄a。", "中仄平平b，", "中仄平平中仄平b。"),
                                     P("中平中仄c，", "中仄中平平仄仄c。", "中仄平平d，", "中仄平平中仄平d。")])]),
    "点绛唇": dict(alias=["点樱桃", "南浦月"], mood="清新婉约", example="李清照「蹴罢秋千」",
                forms=[dict(name="正体", rhymes={"a": "仄"},
                            parts=[P("中仄平平，", "中平中仄平平仄a。", "中平中仄a，", "中仄平平仄a。"),
                                   P("中仄中平，", "中仄平平仄a。", "平平仄a，", "中平中仄a，", "中仄平平仄a。")])]),
    "清平乐": dict(alias=["清平乐令", "醉东风"], mood="上片仄韵、下片平韵，宜叙事写景", example="辛弃疾「茅檐低小」",
                forms=[dict(name="正体", rhymes={"a": "仄", "b": "平"},
                            parts=[P("中平中仄a，", "中仄平平仄a。", "中仄中平平仄仄a，", "中仄中平中仄a。"),
                                   P("中平中仄平平b，", "中平中仄平平b。", "中仄中平中仄，", "中平中仄平平b。")])]),
    "西江月": dict(alias=["白苹香", "步虚词"], mood="平仄通叶，舒徐，宜叙事写景、谐趣", example="辛弃疾「明月别枝惊鹊」",
                note="每片结句押与平韵同部的仄声字（平仄通叶）",
                forms=[dict(name="正体", rhymes={"a": "平", "b": "仄"}, parts=same("中仄中平中仄，", "中平中仄平平a。", "中平中仄仄平平a，", "中仄中平中仄b。"))]),
    "鹧鸪天": dict(alias=["思佳客", "思越人"], mood="声调谐婉，宜抒情", example="晏几道「彩袖殷勤捧玉钟」",
                forms=[dict(name="正体", rhymes={"a": "平"},
                            parts=[P("中仄平平中仄平a，", "中平中仄仄平平a。", "中平中仄平平仄，", "中仄平平中仄平a。"),
                                   P("中仄仄，", "中平平a，", "中平中仄仄平平a。", "中平中仄平平仄，", "中仄平平中仄平a。")])]),
    "虞美人": dict(alias=["一江春水", "玉壶冰"], mood="平仄四换韵，感慨深沉", example="李煜「春花秋月何时了」",
                forms=[dict(name="正体", rhymes={"a": "仄", "b": "平", "c": "仄", "d": "平"},
                            parts=[P("中平中仄平平仄a，", "中仄平平仄a。", "中平中仄仄平平b，", "中仄中平中仄仄平平b。"),
                                   P("中平中仄平平仄c，", "中仄平平仄c。", "中平中仄仄平平d，", "中仄中平中仄仄平平d。")])]),
    "南乡子": dict(alias=["好离乡", "蕉叶怨"], mood="声情激越，宜怀古抒怀", example="辛弃疾「何处望神州」",
                forms=[dict(name="双调", rhymes={"a": "平"}, parts=same("中仄仄平平a，", "中仄平平中仄平a。", "中仄中平平仄仄，", "平平a，", "中仄平平中仄平a。"))]),
    "一剪梅": dict(alias=["一翦梅", "腊梅香", "玉簟秋"], mood="句句押韵，缠绵往复", example="李清照「红藕香残玉簟秋」",
                forms=[dict(name="正体", rhymes={"a": "平"}, parts=same("中仄平平中仄平a，", "中仄平平a?，", "中仄平平a。", "中平中仄仄平平a，", "中仄平平a?，", "中仄平平a。"))]),
    "蝶恋花": dict(alias=["鹊踏枝", "凤栖梧", "黄金缕"], mood="婉转，宜离情春愁", example="苏轼「花褪残红青杏小」、柳永「伫倚危楼风细细」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=same("中仄中平平仄仄a，", "中仄平平，", "中仄平平仄a。", "中仄中平平仄仄a，", "中平中仄平平仄a。"))]),
    "临江仙": dict(alias=["谢新恩", "雁后归"], mood="舒展从容，宜抒怀感旧", example="苏轼「夜饮东坡醒复醉」、晏几道「梦后楼台高锁」",
                forms=[dict(name="六十字体", rhymes={"a": "平"}, parts=same("中仄中平平仄仄，", "中平中仄平平a。", "中平中仄仄平平a。", "中平平仄仄，", "中仄仄平平a。")),
                       dict(name="五十八字体", stats=False, rhymes={"a": "平"}, parts=same("中仄中平中仄，", "中平中仄平平a。", "中平中仄仄平平a。", "中平平仄仄，", "中仄仄平平a。"))]),
    "渔家傲": dict(alias=["渔歌子"], mood="句句押仄韵，宜边塞豪情或羁旅", example="范仲淹「塞下秋来风景异」、李清照「天接云涛连晓雾」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=same("中仄中平平仄仄a，", "中平中仄平平仄a。", "中仄中平平仄仄a。", "中中仄a，", "中平中仄平平仄a。"))]),
    "苏幕遮": dict(alias=["鬓云松令"], mood="宜写景怀乡", example="范仲淹「碧云天」、周邦彦「燎沉香」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=same("中平平，", "中仄仄a。", "中仄平平，", "中仄平平仄a。", "中仄中平平仄仄a。", "中仄平平，", "中仄平平仄a。"))]),
    "定风波": dict(alias=["定风流", "卷春空"], mood="平韵为主、仄韵错叶，宜旷达", example="苏轼「莫听穿林打叶声」",
                forms=[dict(name="正体", rhymes={"a": "平", "b": "仄", "c": "仄", "d": "仄"},
                            parts=[P("中仄中平中仄平a，", "中平中仄仄平平a。", "中仄中平平仄仄b，", "中仄b，", "中平中仄仄平平a。"),
                                   P("中仄中平平仄仄c，", "中仄c，", "中平中仄仄平平a。", "中仄中平平仄仄d，", "中仄d，", "中平中仄仄平平a。")])]),
    "破阵子": dict(alias=["十拍子"], mood="激昂，宜豪情壮志", example="辛弃疾「醉里挑灯看剑」",
                forms=[dict(name="正体", rhymes={"a": "平"}, parts=same("中仄中平中仄，", "中平中仄平平a。", "中仄中平平仄仄，", "中仄平平中仄平a。", "中平中仄平a。"))]),
    "江城子": dict(alias=["江神子", "村意远"], mood="宜豪放，亦宜悼亡", example="苏轼「老夫聊发少年狂」「十年生死两茫茫」",
                forms=[dict(name="双调", rhymes={"a": "平"}, parts=same("中平中仄仄平平a，", "中平平a，", "中平平a。", "中仄中平，", "中仄仄平平a。", "中仄中平平仄仄，", "中仄仄，", "中平平a。"))]),
    "青玉案": dict(alias=["横塘路", "西湖路"], mood="宜婉约深情", example="贺铸「凌波不过横塘路」、辛弃疾「东风夜放花千树」",
                forms=[dict(name="正体", rhymes={"a": "仄"},
                            parts=[P("中平中仄平平仄a，", "中中仄、", "平平仄a。", "中仄中平平仄仄a。", "中平中仄，", "中平中仄a?，", "中仄平平仄a。"),
                                   P("中平中仄平平仄a，", "中仄中平仄平仄a。", "中仄中平平仄仄a。", "中平中仄，", "中平中仄a?，", "中仄平平仄a。")])]),
    "满江红": dict(alias=["上江虹", "念良游"], mood="多押入声，激越豪壮", example="岳飞（传）「怒发冲冠」",
                forms=[dict(name="正体", rhymes={"a": "仄"},
                            parts=[P("中仄平平，", "平中仄、", "中平中仄a。", "中中仄、", "中平中仄，", "中平中仄a。", "中仄中平平仄仄，", "中平中仄平平仄a。", "仄中平、", "中仄仄平平，", "平平仄a。"),
                                   P("中中仄，", "中中仄a。", "中中仄，", "中中仄a。", "仄平平中仄、", "中平中仄a。", "中仄中平平仄仄，", "中平中仄平平仄a。", "仄中平、", "中仄仄平平，", "平平仄a。")])]),
    "水调歌头": dict(alias=["元会曲", "台城游"], mood="雄放开阔，宜旷达怀远", example="苏轼「明月几时有」",
                 forms=[dict(name="正体", rhymes={"a": "平"},
                             parts=[P("中仄中平仄，", "中仄仄平平a。", "中平中仄平仄，", "中仄仄平平a。", "中仄中平中仄，", "中仄中平中仄，", "中仄仄平平a。", "中仄中平仄，", "中仄仄平平a。"),
                                    P("中平仄，", "中仄仄，", "中平平a。", "中平中仄，", "中仄中仄仄平平a。", "中仄中平中仄，", "中仄中平中仄，", "中仄仄平平a。", "中仄中平仄，", "中仄仄平平a。")])]),
    "念奴娇": dict(alias=["百字令", "酹江月", "大江东去", "湘月"], mood="豪迈，宜怀古、咏怀，常押入声", example="苏轼「大江东去」",
                forms=[dict(name="正体", rhymes={"a": "仄"},
                            parts=[P("中平中仄，", "中中中、", "中仄中平平仄a。", "中仄平平，", "中中仄、", "中仄中平平仄a。", "中仄平平，", "中平中仄，", "中仄平平仄a。", "中平中仄，", "中平中仄平仄a。"),
                                   P("中仄中仄平平，", "中平中仄，", "中仄平平仄a。", "中仄平平平仄仄，", "中仄中平平仄a。", "中仄平平，", "中平中仄，", "中仄平平仄a。", "中平中仄，", "中平中仄平仄a。")])]),
    "雨霖铃": dict(alias=["雨淋铃"], mood="凄切缠绵，宜离别", example="柳永「寒蝉凄切」",
                forms=[dict(name="柳永体", rhymes={"a": "仄"},
                            parts=[P("中平中仄a，", "中平中仄，", "中仄平仄a。", "中平中仄平仄，", "中仄仄、", "中平中仄a。", "中仄中平中仄，", "中平中平仄a。", "中仄仄、", "中仄平平，", "中仄中平中平仄a。"),
                                   P("中平中仄平平仄a，", "中中平、", "中仄平平仄a。", "中平中仄平仄，", "中仄仄、", "中平中仄a。", "中仄平平，", "中仄平平、", "中仄平仄a。", "中仄仄、", "中仄平平，", "中仄平平仄a。")])]),
    "声声慢": dict(alias=["胜胜慢", "凤求凰"], mood="李清照仄韵体：叠字起句，凄苦低回", example="李清照「寻寻觅觅」",
                end_tone="仄",
                forms=[dict(name="仄韵体", rhymes={"a": "仄"},
                            parts=[P("中平中仄，", "中平中仄，", "中平中仄平仄a。", "中仄中平中仄，", "中平中仄a。", "中平中仄中仄，", "中中中、", "中平平仄a。", "中中仄，", "中中平，", "中仄中平平仄a。"),
                                   P("中仄中平平仄a，", "中中仄、", "中平中仄平仄a。", "中仄平平，", "中仄中平平仄a。", "中平中平中仄，", "中中平、", "中仄平仄a。", "中中仄，", "中中中、", "中仄中仄a。")])]),
    "永遇乐": dict(alias=["消息"], mood="苍凉沉郁，宜怀古", example="辛弃疾「千古江山」、李清照「落日熔金」",
                forms=[dict(name="正体", rhymes={"a": "仄"},
                            parts=[P("中仄平平，", "中平中仄，", "中仄平仄a。", "中仄平平，", "中平中仄，", "中仄平平仄a。", "中平中仄，", "中平中仄，", "中仄中平平仄a。", "仄平平、", "中平中仄，", "中仄中平平仄a。"),
                                   P("中平中仄，", "中平中仄，", "中仄中平平仄a。", "中仄平平，", "中平中仄，", "中仄平平仄a。", "中平中仄，", "中平中仄，", "中仄中平平仄a。", "仄平仄、", "中平中仄，", "中平中仄a。")])]),
    "沁园春": dict(alias=["寿星明", "东仙"], mood="气势恢宏，多用领字和对句，宜议论抒怀", example="辛弃疾「杯汝来前」、陆游「孤鹤归飞」",
                forms=[dict(name="正体", rhymes={"a": "平"},
                            parts=[P("中仄平平，", "中仄平平，", "中仄仄平a。", "仄中平中仄，", "中平中仄，", "中平中仄，", "中仄平平a。", "中仄平平，", "中平中仄，", "中仄平平中仄平a。", "平平仄，", "仄中平中仄，", "中仄平平a。"),
                                   P("中平中仄平平a，", "仄中仄平平中仄平a。", "仄中平中仄，", "中平中仄，", "中平中仄，", "中仄平平a。", "中仄平平，", "中平中仄，", "中仄平平中仄平a。", "平平仄，", "仄中平中仄，", "中仄平平a。")])]),
    "贺新郎": dict(alias=["金缕曲", "乳燕飞", "贺新凉"], mood="沉郁苍凉，宜慷慨悲歌", example="辛弃疾「甚矣吾衰矣」",
                forms=[dict(name="正体", rhymes={"a": "仄"},
                            parts=[P("中仄平平仄a，", "仄平平、", "中平中仄，", "中平平仄a。", "中仄中平平仄仄，", "中仄中平中仄a。", "仄中仄、", "中平平仄a。", "中仄中平平仄仄，", "仄中平、", "中仄平平仄a。", "平仄仄，", "仄平仄a。"),
                                   P("中平中仄平平仄a，", "仄平平、", "中平中仄，", "中平平仄a。", "中仄中平平仄仄，", "中仄中平中仄a。", "仄中仄、", "中平平仄a。", "中仄中平平仄仄，", "仄中平、", "中仄平平仄a。", "平仄仄，", "仄平仄a。")])]),
    "钗头凤": dict(alias=["撷芳词", "折红英"], mood="三字句急促、叠字收煞，凄紧悲怆", example="陆游「红酥手」",
                forms=[dict(name="正体", rhymes={"a": "仄", "b": "仄", "c": "仄", "d": "仄"},
                            parts=[P("中平仄a，", "中平仄a，", "中平中仄平平仄a。", "平平仄b，", "平平仄b。", "中平中仄，", "中平中仄b。", "仄b，", "仄b，", "仄b。"),
                                   P("中平仄c，", "中平仄c，", "中平中仄平平仄c。", "平平仄d，", "平平仄d。", "中平中仄，", "中平中仄d。", "仄d，", "仄d，", "仄d。")])]),
    "生查子": dict(alias=["相和柳", "晴色入青山"], mood="近五言古绝，宜相思", example="欧阳修（一作朱淑真）「去年元夜时」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=same("中平中仄平，", "中仄平平仄a。", "中仄仄平平，", "中仄平平仄a。"))]),
    "醉花阴": dict(alias=[], mood="宜闺怨秋思", example="李清照「薄雾浓云愁永昼」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=same("中仄中平平仄仄a，", "中仄平平仄a。", "中仄仄平平，", "中仄平平，", "中仄平平仄a。"))]),
    "踏莎行": dict(alias=["柳长春", "喜朝天"], mood="宜羁旅离情", example="秦观「雾失楼台」、欧阳修「候馆梅残」",
                forms=[dict(name="正体", rhymes={"a": "仄"}, parts=same("中仄平平，", "中平中仄a，", "中平中仄平平仄a。", "中平中仄仄平平，", "中平中仄平平仄a。"))]),
    "浪淘沙令": dict(alias=["浪淘沙", "卖花声"], mood="宜感慨今昔", example="李煜「帘外雨潺潺」",
                 forms=[dict(name="正体", rhymes={"a": "平"}, parts=same("中仄仄平平a，", "中仄平平a。", "中平中仄仄平平a。", "中仄中平平仄仄，", "中仄平平a。"))]),
    "忆秦娥": dict(alias=["秦楼月", "碧云深"], mood="多押入声、有叠句，悲壮苍凉", example="李白（传）「箫声咽」",
                forms=[dict(name="正体", rhymes={"a": "仄"},
                            parts=[P("平平仄a，", "中平中仄平平仄a。", "平平仄a，", "中平中仄，", "中平平仄a。"),
                                   P("中平中仄平平仄a，", "中平中仄平平仄a。", "平平仄a，", "中平中仄，", "中平平仄a。")])]),
    "武陵春": dict(alias=["武林春", "花想容"], mood="宜愁思", example="李清照「风住尘香花已尽」",
                forms=[dict(name="正体", rhymes={"a": "平"}, parts=same("中仄中平平仄仄，", "中仄仄平平a。", "中仄平平中仄平a，", "中仄仄平平a。")),
                       dict(name="又一体（结句六字）", rhymes={"a": "平"},
                            parts=[P("中仄中平平仄仄，", "中仄仄平平a。", "中仄平平中仄平a，", "中仄仄平平a。"),
                                   P("中仄中平平仄仄，", "中仄仄平平a。", "中仄平平中仄平，", "中仄仄、", "仄平平a。")])]),
    "八声甘州": dict(alias=["甘州", "潇潇雨"], mood="雄浑苍凉，宜登临怀远", example="柳永「对潇潇暮雨洒江天」",
                 forms=[dict(name="正体", rhymes={"a": "平"},
                             parts=[P("仄平平中仄仄平平，", "中仄仄平平a。", "仄平平中仄，", "中平中仄，", "中仄平平a。", "中仄中平中仄，", "中仄仄平平a。", "中仄平平仄，", "中仄平平a。"),
                                    P("中仄中平中仄，", "仄中平中仄，", "中仄平平a。", "仄中平中仄，", "中仄仄平平a。", "仄平平、", "中平中仄，", "仄中仄、", "中仄仄平平a。", "中平仄、", "中平中仄，", "中仄平平a。")])]),
}


def seg_parts(seg):
    punct = seg[-1] if seg[-1] in "，。、；" else ""
    core = seg[:-1] if punct else seg
    label = ""
    while core and core[-1] not in "平仄中":
        label = core[-1] + label
        core = core[:-1]
    return core, label, punct


def total(form):
    return sum(len(seg_parts(s)[0]) for part in form["parts"] for s in part)


def samples(con, name, alias):
    names = [name] + alias
    out = []
    for rhythmic, author, content in con.execute("select rhythmic, author, content from ci"):
        base = re.split(r"[·\s]", rhythmic.strip())[0]
        if base in names and content:
            out.append((author, "".join(HAN.findall(content.split(">>")[0]))))
    return out


def build(con, verbose):
    table = {}
    for name, spec in SPEC.items():
        allp = samples(con, name, spec["alias"])
        forms_out = []
        for form in spec["forms"]:
            n = total(form)
            texts = [t for _, t in allp if len(t) == n] if form.get("stats", True) else []
            if spec.get("end_tone"):
                texts = [t for t in texts if D.char_tone(t[-1]).tones == {spec["end_tone"]}]
            # per-position tone stats
            stats = [collections.Counter() for _ in range(n)]
            for t in texts:
                for i, ch in enumerate(t):
                    tones = D.char_tone(ch).tones
                    if len(tones) == 1:
                        stats[i][next(iter(tones))] += 1
            pos = 0
            parts_out, changes = [], []
            for part in form["parts"]:
                segs_out = []
                for seg in part:
                    core, label, punct = seg_parts(seg)
                    new = []
                    for j, mem in enumerate(core):
                        c = stats[pos + j]
                        k = c["平"] + c["仄"]
                        share = c["平"] / k if k else 0.5
                        if label and j == len(core) - 1:
                            val = "中" if label.endswith("?") else form["rhymes"][label]
                        elif k >= 12 and share >= 0.88:
                            val = "平"
                        elif k >= 12 and share <= 0.12:
                            val = "仄"
                        elif k >= 12:
                            val = "中"
                        elif 3 <= k < 12:
                            # 样本少：全体一致才定死，否则放宽为可平可仄
                            val = "平" if share == 1.0 else ("仄" if share == 0.0 else "中")
                        else:
                            val = mem
                        if val != mem:
                            changes.append("%d:%s→%s(平%.0f%%,n=%d)" % (pos + j + 1, mem, val, 100 * share, k))
                        new.append(val)
                    segs_out.append("".join(new) + label + punct)
                    pos += len(core)
                parts_out.append(segs_out)
            # rhyme sanity: share of samples whose rhyme positions agree
            agree = rhyme_agreement(texts, form)
            forms_out.append({"name": form["name"], "rhymes": form["rhymes"], "parts": parts_out})
            print("%-6s %-10s %3d字  样本 %3d  韵位一致 %s  %s" % (
                name, form["name"], n, len(texts), agree, ("改动 " + " ".join(changes)) if verbose else "改动 %d 处" % len(changes)))
        size = total(spec["forms"][0])
        entry = {"alias": spec["alias"], "length": "小令" if size <= 58 else ("中调" if size <= 90 else "长调"),
                 "desc": describe(spec["forms"][0]), "mood": spec["mood"], "example": spec["example"], "forms": forms_out}
        if spec.get("note"):
            entry["desc"] += "；" + spec["note"]
        table[name] = entry
    return table


def rhyme_agreement(texts, form):
    if not texts:
        return "—"
    ends = collections.defaultdict(list)
    pos = 0
    for part in form["parts"]:
        for seg in part:
            core, label, _ = seg_parts(seg)
            pos += len(core)
            if label and not label.endswith("?"):
                ends[label].append(pos - 1)
    ok = tot = 0
    for t in texts:
        for label, idx in ends.items():
            tone = "平" if form["rhymes"][label] == "平" else "仄"
            keys = [D.rhyme_keys(t[i], "cilin", tone) for i in idx]
            c = collections.Counter(k for ks in keys for k in ks)
            if not c:
                continue
            best = max(c, key=c.get)
            ok += sum(1 for ks in keys if best in ks or any(k[1] == "入" and best[1] == "入" for k in ks))
            tot += len(keys)
    return "%.0f%%" % (100.0 * ok / tot) if tot else "—"


def describe(form):
    n = total(form)
    parts = len(form["parts"])
    tones = set(form["rhymes"].values())
    kind = "平韵" if tones == {"平"} else ("仄韵" if tones == {"仄"} else "平仄韵转换")
    return "%s%d字，%s" % ({1: "单调", 2: "双调"}.get(parts, "%d叠" % parts), n, kind)


if __name__ == "__main__":
    db, skill = sys.argv[1], sys.argv[2]
    table = build(sqlite3.connect(db), "-v" in sys.argv)
    path = os.path.join(skill, "assets", "cipai.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=1)
    print("wrote", path, len(table), "词牌")
