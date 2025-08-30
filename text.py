import pickle
from cryptography.fernet import Fernet

def generate_key():
    """
    生成一个密钥（只需执行一次，然后保存起来）。
    """
    return Fernet.generate_key()

def save_encrypted(obj, filename, key):
    """
    使用 pickle 序列化并加密对象，保存到文件
    """
    f = Fernet(key)
    data = pickle.dumps(obj)         # 序列化为 bytes
    encrypted = f.encrypt(data)      # 加密
    with open(filename, "wb") as f_out:
        f_out.write(encrypted)

def load_encrypted(filename, key):
    """
    从加密文件中解密并反序列化对象
    """
    f = Fernet(key)
    with open(filename, "rb") as f_in:
        encrypted = f_in.read()
    data = f.decrypt(encrypted)      # 解密
    return pickle.loads(data)        # 反序列化回 Python 对象


if __name__ == '__main__':
    # 词条数据[玩家, 卧底]
    word_pairs = [
    ]
    key = generate_key()
    with open("data/KEY", "wb") as f:
        f.write(key)

    save_encrypted(word_pairs, "data/WORDS", key)
    with open("data/KEY", "rb") as f:
        key = f.read()

    loaded_pairs = load_encrypted("data/WORDS", key)
    print(loaded_pairs)
