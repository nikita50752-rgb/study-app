# Зашифрованная синхронизация «Рабочий стол\Учёба\Приложение» → Telegram Mini App (GitHub Pages).
# В интернет попадают только зашифрованные (AES-256-GCM) файлы с случайными именами.
# Ключ лежит только на этом ПК (KEYFILE) и в ссылке кнопки бота в личном чате.
import os, re, json, hmac, hashlib, base64, subprocess, datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SRC = os.path.expanduser(r'~\Desktop\Учёба\Приложение')
REPO = os.path.dirname(os.path.abspath(__file__))
KEYFILE = os.path.expanduser(r'~\.study-app-key')
STATE = os.path.join(REPO, 'state.json')       # в .gitignore
LOG = os.path.join(REPO, 'sync_log.txt')       # в .gitignore
DST = os.path.join(REPO, 'd')
GIT = r'C:\Program Files\Git\cmd\git.exe'
EXT = {'.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg', '.pptx', '.ppt', '.xlsx', '.xls', '.txt', '.cdw', '.frw', '.zip'}
MAXSIZE = 50 * 1024 * 1024
nat = lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(datetime.datetime.now().strftime('%d.%m.%Y %H:%M ') + msg + '\n')


def get_key():
    if not os.path.exists(KEYFILE):
        with open(KEYFILE, 'w') as f:
            f.write(base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip('='))
    s = open(KEYFILE).read().strip()
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def enc(key, data):
    iv = os.urandom(12)
    return iv + AESGCM(key).encrypt(iv, data, None)


def main():
    if not os.path.isdir(SRC):
        return
    key = get_key()
    state = json.load(open(STATE, encoding='utf-8')) if os.path.exists(STATE) else {}
    os.makedirs(DST, exist_ok=True)
    items, keep = [], set()
    for cat in sorted(os.listdir(SRC), key=nat):
        cdir = os.path.join(SRC, cat)
        if not os.path.isdir(cdir) or cat.startswith('.'):
            continue
        for name in sorted(os.listdir(cdir), key=nat):
            p = os.path.join(cdir, name)
            ext = os.path.splitext(name)[1].lower()
            if (not os.path.isfile(p) or name.startswith(('~$', '.')) or ext not in EXT
                    or os.path.getsize(p) > MAXSIZE):
                continue
            rel = cat + '/' + name
            fid = hmac.new(key, rel.encode(), hashlib.sha256).hexdigest()[:24]
            keep.add(fid)
            st = os.stat(p)
            sig = [st.st_size, int(st.st_mtime)]
            out = os.path.join(DST, fid + '.bin')
            if state.get(rel) != sig or not os.path.exists(out):
                with open(p, 'rb') as f:
                    data = f.read()
                with open(out, 'wb') as f:
                    f.write(enc(key, data))
                state[rel] = sig
            items.append({'cat': cat, 'name': os.path.splitext(name)[0], 'ext': ext.lstrip('.'),
                          'date': datetime.datetime.fromtimestamp(st.st_mtime).strftime('%d.%m.%Y'),
                          'size': st.st_size, 'id': fid, 'file': name})
    for n in os.listdir(DST):
        if n.endswith('.bin') and n[:-4] not in keep:
            os.remove(os.path.join(DST, n))
    state = {k: v for k, v in state.items()
             if hmac.new(key, k.encode(), hashlib.sha256).hexdigest()[:24] in keep}
    json.dump(state, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False)

    index = json.dumps(items, ensure_ascii=False, sort_keys=True).encode()
    old = os.path.join(REPO, 'index.sig')                 # чтобы не перешифровывать список без изменений
    h = hashlib.sha256(index).hexdigest()
    if not (os.path.exists(old) and open(old).read() == h) or not os.path.exists(os.path.join(REPO, 'index.bin')):
        with open(os.path.join(REPO, 'index.bin'), 'wb') as f:
            f.write(enc(key, index))
        open(old, 'w').write(h)

    run = lambda *a: subprocess.run([GIT, '-C', REPO, *a], capture_output=True, text=True, encoding='utf-8',
                                    creationflags=0x08000000)
    run('add', '-A')
    if not run('status', '--porcelain').stdout.strip():
        return
    run('-c', 'user.name=nikita50752-rgb', '-c', 'user.email=357074759+nikita50752-rgb@users.noreply.github.com',
        'commit', '-qm', 'update')
    r = run('push', '-q')
    log(('OK, файлов: %d' % len(items)) if r.returncode == 0 else 'ОШИБКА push: ' + r.stderr.strip()[:300])


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log('ОШИБКА: %r' % e)
