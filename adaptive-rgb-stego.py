import numpy as np
# pillow, fork do Python Imaging Library, usprawnia pracę na plikach 
from PIL import Image # moduł do pracy z obrazem
from statistics import median, variance
from pathlib import Path

BASE_DIR = Path(__file__).parent

# zmienne

pict1 = BASE_DIR / "pict1.png"  # "thumbnail" do przerobienia na bity
pict2 = BASE_DIR / "pict2.png"  # 512x512
pict3 = BASE_DIR / "pict3.png"  # 1024x1024
pict4 = BASE_DIR / "plain.png"
pict5 = BASE_DIR / "textured.png"
pict6 = BASE_DIR / "edgy.png"

short_msg = "keskiajan syksy"
long_msg = BASE_DIR / "kalevala.txt"
stego_out = BASE_DIR / "stego_out.png"

print("Wybierz obraz do ukrycia w nim tajnej treści: ")
print("   #1   512x512")
print("   #2   1024x1024")
print("   #3   gładki") 
print("   #4   teksturowany")
print("   #5   z krawędziami")

img_case = int(input("Twój wybór: "))
match img_case:
    case 1:
        img_path = pict2
    case 2:
        img_path = pict3
    case 3:
        img_path = pict4
    case 4:
        img_path = pict5
    case 5:
        img_path = pict6        
    case _:
        print("Niepoprawny wybór.")
        exit()
print("Wybrany obraz:", img_path)

img = Image.open(img_path)
if img.mode != "RGB":   # sprawdzenie, czy wczytany obraz jest w RGB, jeśli nie:
    img = img.convert("RGB") # konwersja 

width, height = img.size # szerokość, wysokość obrazu wypakowane z tuple
pixelz = img.load()

print("Wybierz co chcesz osadzić w obrazie jako ukrytą wiadomość: ")
print("   #1   krótka wiadomość")
print("   #2   długa wiadomość")
print("   #3   obraz")

msg_case = int(input("Twój wybór: "))
match msg_case:
    case 1:
        msg = short_msg
    case 2:
        msg = long_msg
    case 3:
        msg = pict1
    case _:
        print("Niepoprawny wybór.")
        exit()

print("Wybrałeś: ", msg)

def input_to_bin(msg): 
    if msg == short_msg:
    # zamiana tekstów zadeklarowanych wcześniej wiadomości na ich reprezentacje binarne (1 znak = 8 bitów)
        msg = ''.join(format(ord(m), '08b') for m in msg) + '11111110' 
        preql = format(len(msg), '032b') # wyliczenie długości wiadomości i przedst. jej jako liczby 32-bitowej
        msg = preql + msg
        return msg
    elif msg == long_msg:
        with open(long_msg, "rt", encoding="utf-8") as f:
            txt = f.read()
        # zamiana tekstu na bajty i ich 8-bitowy zapis
        msg2 = ''.join(f'{t:08b}' for t in txt.encode("utf-8")) + '11111110'
        preql2 = format(len(msg2), '032b')
        msg2 = preql2 + msg2   
        with open(BASE_DIR / "bin_kalevala.txt", "wt", encoding="utf-8") as f:
            f.write(msg2)            
        return msg2
    elif msg == pict1: 
        # zamiana obrazu na plik binarny
        m_img = Image.open(pict1).convert("RGB")
        m_x, m_y = m_img.size
        m_pixelz = m_img.load()
        bin_pictmsg = []
        for y in range(m_y):
            for x in range(m_x):
                r, g, b = m_pixelz[x, y]
                for ch in (r, g, b):
                    bin_pictmsg.append(format(ch, '08b'))
        flat = ''.join(bin_pictmsg)  # bez sentinela
        preql3 = format(len(flat), '032b')
        return preql3 + flat

# osadzenie adaptacyjne danych w RBG
def adapt_embb(img, msg, stego_out):
    bloxlist = [] # lista bloków po podziale
    # dzieli obrazy na bloki 8x8
    for y in range(0, height, 8):
        for x in range(0, width, 8):            
            single_block = []
            for b_y in range(y, min(y+8, height)):
                for b_x in range(x, min(x+8, width)):
                    single_block.append((b_x, b_y))
            bloxlist.append(single_block)

    # wariancja jasności
    variances = []
    for single_block in bloxlist: # każdy pixel z bloku
        lux = [] # tabela luminancji pojedynczego bloku
        for p_x, p_y in single_block:
            r, g, b = pixelz[p_x, p_y]
            luminance =  (r + g + b) / 3 # umownie - średnia z wartości 3 nasyceń barw kanałów
            lux.append(luminance)
        var_lux = variance(lux) if len(lux) > 1 else 0.0 # wariancja jasności pojedynczego bloku
        variances.append(var_lux)
    #print(lux)  
    print(variances)

    # próg teksturowalności
    threshold = median(variances)
    new_bloxlist = []
    for single_block, var_lux in zip(bloxlist, variances):
        if var_lux > threshold:
            new_bloxlist.append(single_block)
         
    # osadzanie lsb - 16bit-owe
    BITZ_CH = 2 # liczba lsb do modyfikacji
    MASK = 0xFF ^ ((1 << BITZ_CH) - 1) # maska zerująca 2 lsb
    BITZ_BLOCK = 16 # docelowa liczba bitów do osadzenia w pojedynczym bloku
    bit_index = 0
    len_msg = len(msg)

    # sprawdzenie pojemności
    active_pixels = sum(len(b) for b in new_bloxlist)
    available = active_pixels * BITZ_CH * 3   # 2 LSB × 3 kanały na piksel
    if available < len_msg:
        raise ValueError(
            f"Za mało miejsca! Potrzeba {len_msg} bitów, dostępnych {available}."
        )
    print(f"Pojemność OK: potrzeba {len_msg} b, dostępnych {available} b")

    for single_block in new_bloxlist: # każdy z bloków, które przekroczyły określ. próg teksturowalności
        bits_block = 0
        for (p_x, p_y) in single_block: # iteracja po współrzędnych
            if bit_index >= len_msg or bits_block >= BITZ_BLOCK:
                break
            r, g, b = pixelz[p_x, p_y]
            channelz = [r, g, b]
            b_lsb = []
            for c in channelz:
                if bit_index >= len_msg or bits_block >= BITZ_BLOCK:
                    b_lsb.append(c) # nie będzie nowych bitów do osadzenia
                    continue
                # osadzenie BITZ_CH w kanale
                bitz = 0
                for shft in range(BITZ_CH - 1, -1, -1): 
                    if bit_index < len_msg and bits_block < BITZ_BLOCK:
                        bitz = bitz | int(msg[bit_index]) << shft   
                        bit_index += 1
                        bits_block += 1 
                c = (c & MASK) | bitz # zeruje 2 lsb, wypisuje 2 bity hidden contentu
                b_lsb.append(c)
            pixelz[p_x,p_y] = tuple(b_lsb)
        if bit_index >= len_msg:
            break           
    img.save(stego_out)
    return stego_out 
 
# odczytywanie ukrytej zawartości (dla tekstu)
def extr_emb(stego_out):
    img = Image.open(stego_out)
    width, height = img.size 
    pixelz = img.load()

    # odbudowa bloków 8x8
    bloxlist = [] # lista na bloki po podziale
    for y in range(0, height, 8):
        for x in range(0, width, 8):            
            single_block = []
            for b_y in range(y, min(y+8, height)):
                for b_x in range(x, min(x+8, width)):
                    single_block.append((b_x, b_y))
            bloxlist.append(single_block)
        #print(bloxlist)

    variances = []   # wariancje jasności
    for single_block in bloxlist: 
        lux = [] # tabela luminancji pojedynczego bloku
        for p_x, p_y in single_block:
            r, g, b = pixelz[p_x, p_y]
            luminance =  (r + g + b) / 3 # umownie - średnia z wartości 3 nasyceń barw kanałów
            lux.append(luminance)
        var_lux = variance(lux) if len(lux) > 1 else 0.0 # wariancja jasności pojedynczego bloku
        variances.append(var_lux)
    print(variances)

    threshold = median(variances)
    new_bloxlist = [] 
    for single_block, var_lux in zip(bloxlist, variances):
        if var_lux > threshold:
            new_bloxlist.append(single_block)

    BITZ_CH = 2 
    BITZ_BLOCK = 16
    bits_string = ''

    for single_block in new_bloxlist:
        bits_block = 0
        for p_x, p_y in single_block:
            if bits_block >= BITZ_BLOCK:
                break
            r, g, b = pixelz[p_x, p_y]
            for c in (r, g, b): 
                if bits_block >= BITZ_BLOCK:
                    break
                for shft in range(BITZ_CH - 1, -1, -1):
                    bits_string += str((c >> shft) & 1)
                    bits_block += 1 
                    if bits_block >= BITZ_BLOCK:
                        break

    # długość wiadomości z 32-bitowego nagłówka - odczyt
    if len(bits_string) < 32:
        print("Niewystarczająca ilość danych, aby odczytać nagłówek wiadomości.")
        return 0
    header = int(bits_string[:32], 2) # z binarnego stringa
    payload = bits_string[32:32 + header] #właściwa wiadomość, po wycięciu nagłówka

    # bity na znaki — sentinel '11111110' jest bezpieczny tu, bo to tekst
    revealed_bitstr = '' 
    for i in range(0, len(payload), 8):
        if i + 8 > len(payload):
            break
        byte = payload[i:i+8]
        if byte == '11111110':
            break       
        revealed_bitstr += chr(int(byte,2))
    print(revealed_bitstr)
    return revealed_bitstr


def extr_emb_image(stego_out, original_hidden_pict, recovered_out=None):
    img = Image.open(stego_out)
    width, height = img.size 
    pixelz = img.load()

    bloxlist = []
    for y in range(0, height, 8):
        for x in range(0, width, 8):
            single_block = []
            for b_y in range(y, min(y+8, height)):
                for b_x in range(x, min(x+8, width)):
                    single_block.append((b_x, b_y))
            bloxlist.append(single_block)

    variances = []
    for single_block in bloxlist:
        lux = []
        for p_x, p_y in single_block:
            r, g, b = pixelz[p_x, p_y]
            lux.append((r + g + b) / 3)
        variances.append(variance(lux) if len(lux) > 1 else 0.0)

    threshold = median(variances)
    new_bloxlist = [b for b, v in zip(bloxlist, variances) if v > threshold]

    BITZ_CH = 2
    BITZ_BLOCK = 16
    bits_string = ''
    for single_block in new_bloxlist:
        bits_block = 0
        for p_x, p_y in single_block:
            if bits_block >= BITZ_BLOCK:
                break
            r, g, b = pixelz[p_x, p_y]
            for c in (r, g, b):
                if bits_block >= BITZ_BLOCK:
                    break
                for shft in range(BITZ_CH - 1, -1, -1):
                    bits_string += str((c >> shft) & 1)
                    bits_block += 1
                    if bits_block >= BITZ_BLOCK:
                        break

    if len(bits_string) < 32:
        print("Niewystarczająca ilość danych, aby odczytać nagłówek wiadomości.")
        return None
    header = int(bits_string[:32], 2)
    payload = bits_string[32:32 + header]

    if len(payload) < header:
        print(f"Uwaga: odczytano tylko {len(payload)} z {header} bitów payloadu.")

    # bity na bajty (wartości pikseli) — nie sprawdzania sentinela,
    # bierze się dokładnie tyle bajtów ile mówi nagłówek długości
    byte_vals = []
    for i in range(0, len(payload), 8):
        if i + 8 > len(payload):
            break
        byte = payload[i:i+8]
        byte_vals.append(int(byte, 2))

    # wymiary bierze się z oryginalnego obrazu ukrytego (pict1) — input_to_bin
    # nie zapisuje wymiarów w nagłówku, więc trzeba je znać z zewnątrz
    m_img = Image.open(original_hidden_pict).convert("RGB")
    m_x, m_y = m_img.size

    expected_bytes = m_x * m_y * 3
    if len(byte_vals) < expected_bytes:
        print(f"Uwaga: odczytano {len(byte_vals)} bajtów, oczekiwano {expected_bytes}.")
        byte_vals += [0] * (expected_bytes - len(byte_vals))

    recovered = Image.frombytes("RGB", (m_x, m_y), bytes(byte_vals[:expected_bytes]))
    out_path = recovered_out or (BASE_DIR / "recovered.png")
    recovered.save(out_path)
    return out_path


# PSNR ratio: 10 * log10( MAX^2 / MSE )
def psnr(real_pict, embedded_in_pict):
    # wczytywanie obrazów jako numpy arrays - wymóg przy użyciu np.mean
    rel_array = np.array(Image.open(real_pict).convert("RGB"), dtype=np.float64)
    emb_array = np.array(Image.open(embedded_in_pict).convert("RGB"), dtype=np.float64)
    # wartość MSE: średnia z (oryginał - zmodyfikowany)^2
    mse = np.mean((rel_array - emb_array)**2)
    if mse == 0:
        return float('inf')
    # PSNR ratio: 10 * log10( MAX^2 / MSE ), maximum = 255
    psnr_val = 10 * np.log10((255 ** 2) / mse)
    return psnr_val

2
### testy ###
# poprawność ukrywania i odczytywania
msg_bits = input_to_bin(msg)
print(adapt_embb(img, msg_bits, stego_out))

if msg_case == 3:
    # odczyt obrazu z powrotem do .png — to są bajty pikseli, nie znaki tekstu
    recovered_path = extr_emb_image(stego_out, pict1)
    print("Odtworzony obraz zapisany jako:", recovered_path)
else:
    print(extr_emb(stego_out))

print("PSNR:", psnr(img_path, stego_out))
