"""Pure typography/layout policy shared by the desktop UI and headless tests."""
FONT_CANDIDATES = ('Segoe UI', 'Inter', 'Noto Sans', 'DejaVu Sans', 'Liberation Sans', 'Arial')
MONO_CANDIDATES = ('Cascadia Code', 'DejaVu Sans Mono', 'Liberation Mono', 'Courier New')
PALETTE = dict(navy='#132E40', slate='#234458', gold='#C7A76D', paper='#F4F2ED', white='#FFFFFF',
               ink='#203442', muted='#526674', border='#D7DFE3', pale='#E9EEF0')
POINT_SIZES = dict(body=12, small=11, title=22, heading=18, bold=12, tab=11, mono=11)

def choose_family(available, candidates=FONT_CANDIDATES):
    families={str(name).casefold():str(name) for name in available}
    return next((families[name.casefold()] for name in candidates if name.casefold() in families), 'TkDefaultFont')

def readable_scaling(value):
    """Repair absurd/sub-96dpi virtual display settings, without scaling sizes twice."""
    try:scale=float(value)
    except (TypeError,ValueError):return 4/3
    return scale if 4/3 <= scale <= 4 else 4/3

def initial_geometry(screen_width,screen_height):
    # Initial non-maximized fallback fits a 1280x800 desktop including window chrome.
    width=min(1280,max(860,int(screen_width)-40))
    height=min(860,max(480,int(screen_height)-80))
    return f'{width}x{height}+{max(0,(int(screen_width)-width)//2)}+20'


def wheel_units(button,delta):
    """Linux button wheels and Windows/macOS delta wheels, without focus theft."""
    if button==4:return -3
    if button==5:return 3
    return -max(1,abs(int(delta))//120)*3 if delta>0 else max(1,abs(int(delta))//120)*3 if delta<0 else 0


def preview_geometry(screen_width,screen_height):
    """Screen-bounded client rect, reserving decoration/taskbar space."""
    width=max(1,min(980,int(screen_width)-64));height=max(1,min(700,int(screen_height)-100))
    x=max(0,(int(screen_width)-width)//2);y=max(0,(int(screen_height)-height)//2-12)
    return f'{width}x{height}+{x}+{y}',(min(760,width),min(420,height))
