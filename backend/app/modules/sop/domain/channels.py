"""报表渠道归类；事实表保留原始部门，便于核对来源。"""

REPORT_CHANNEL_ALIASES = {
    "国际渠道销售一部": ("国际渠道销售一部", "海外渠道一部", "海外渠道销售一部"),
    "国际渠道销售二部": ("国际渠道销售二部", "海外渠道二部", "海外渠道销售二部"),
    "海外电商": ("海外电商", "海外电商销售部"),
    "国内渠道": ("国内渠道", "国内渠道销售部"),
    "国内电商": ("国内电商", "国内电商销售部"),
}
REPORT_CHANNELS = (*REPORT_CHANNEL_ALIASES, "其他")
ROLLUP_CHANNELS = {"ALL", "全部渠道", "全渠道", "全国渠道", "全部"}
RETAINED_CHANNEL_NAMES = tuple(name for names in REPORT_CHANNEL_ALIASES.values() for name in names)


def normalize_report_channel(channel: str) -> str:
    value = channel.strip()
    for canonical, aliases in REPORT_CHANNEL_ALIASES.items():
        if value in aliases:
            return canonical
    return "其他"
