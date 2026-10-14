file_path = r'mission_2\scripts\demo_pipeline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

start_finally = text.find('finally:')
end_finally = text.find('if __name__', start_finally)

new_finally = """finally:
        logger.info("Kaynaklar serbest braklyor...")
        try:
            if 'cap' in locals() and hasattr(cap, 'release'): cap.release()
        except: pass
        try:
            if 'conn' in locals() and hasattr(conn, 'close'): conn.close()
        except: pass
        try:
            if 'server_sock' in locals() and hasattr(server_sock, 'close'): server_sock.close()
        except: pass
        try:
            if 'out' in locals() and hasattr(out, 'release'): out.release()
        except: pass
        cv2.destroyAllWindows()

"""
text = text[:start_finally] + new_finally + text[end_finally:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
