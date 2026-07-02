from typing import Dict

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import NameRecord


def get_all_unicode_cmap(font: TTFont) -> Dict[int, str]:
    all_cmap = {}
    for subtable in font["cmap"].tables:
        if subtable.format in (4, 12, 10):
            cmap = subtable.cmap
            all_cmap.update(cmap)
    return all_cmap


def set_meta(font: TTFont, new_names: Dict[str, str]) -> None:
    name_ids = {"family": 1, "style": 2, "full_name": 4, "version": 5, "copyright": 0}

    name_table = font["name"]
    name_type_map = {v: k for k, v in name_ids.items()}

    # 收集原始字体中已有的所有名称记录的平台/语言配置
    existing_configs = {}
    for record in name_table.names:
        name_type = name_type_map.get(record.nameID)
        if not name_type:
            continue

        config_key = (record.platformID, record.platEncID, record.langID, record.nameID)
        existing_configs[config_key] = record

    # 处理需要修改的名称
    for name_type, name_id in name_ids.items():
        if name_type not in new_names or not new_names[name_type]:
            continue

        new_value = new_names[name_type]
        type_configs = [k for k in existing_configs.keys() if k[3] == name_id]

        if type_configs:
            for config in type_configs:
                record = existing_configs[config]
                try:
                    record.string = new_value.encode(record.getEncoding())
                except (UnicodeEncodeError, LookupError):
                    record.string = new_value.encode("utf-16be")
        else:
            # 没有现有配置，创建默认配置（Unicode平台，兼容现代系统）
            print(f"警告: 字体中未找到 {name_type} 的记录，将创建默认配置")
            new_record = NameRecord()
            new_record.nameID = name_id
            new_record.platformID = 0  # Unicode平台
            new_record.platEncID = 3  # Unicode 2.0+
            new_record.langID = 0x0409  # 英语(美国) - 通用默认
            new_record.string = new_value.encode("utf-16be")
            name_table.names.append(new_record)
