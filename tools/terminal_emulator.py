import re

class TerminalScreen:
    def __init__(self, cols=120, rows=30):
        self.cols = cols
        self.rows = rows
        self.clear()
        
        # CSI: ESC [ ... <letter>
        self.csi_re = re.compile(r'^\x1b\[([?<=>;0-9]*)([A-Za-z@])')
        # OSC: ESC ] ... (ST or BEL)
        self.osc_re = re.compile(r'^\x1b\].*?(\x1b\\|\x07)')
        # ESC + one char (like ESC ( B)
        self.esc_re = re.compile(r'^\x1b[\(\)\[\]\=>#]')

    def clear(self):
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.cursor_x = 0
        self.cursor_y = 0

    def get_text(self):
        # Join lines and rstrip them
        return "\n".join("".join(row).rstrip() for row in self.grid)

    def feed(self, data):
        i = 0
        while i < len(data):
            char = data[i]
            
            if char == '\x1b':
                # Try CSI
                match = self.csi_re.match(data[i:])
                if match:
                    params = match.group(1).split(';')
                    command = match.group(2)
                    self._handle_csi(params, command)
                    i += len(match.group(0))
                    continue
                
                # Try OSC
                match = self.osc_re.match(data[i:])
                if match:
                    i += len(match.group(0))
                    continue
                
                # Try generic ESC + 1
                match = self.esc_re.match(data[i:])
                if match:
                    consumed = len(match.group(0))
                    # Handle charset sequences like \x1b(B
                    if i + consumed < len(data) and match.group(1) in '()':
                        consumed += 1
                    i += consumed
                    continue
                
                # If we hit an ESC but no match, skip it to avoid loop
                i += 1
                continue
            
            if char == '\r':
                self.cursor_x = 0
            elif char == '\n':
                self.cursor_y += 1
                if self.cursor_y >= self.rows:
                    self._scroll()
                    self.cursor_y = self.rows - 1
            elif char == '\b':
                self.cursor_x = max(0, self.cursor_x - 1)
            elif char == '\t':
                self.cursor_x = (self.cursor_x // 8 + 1) * 8
            elif ord(char) < 32 and char not in ('\r', '\n', '\t', '\b'):
                # Skip other control chars
                pass
            else:
                # Regular character
                if 0 <= self.cursor_y < self.rows and 0 <= self.cursor_x < self.cols:
                    self.grid[self.cursor_y][self.cursor_x] = char
                self.cursor_x += 1
                if self.cursor_x >= self.cols:
                    self.cursor_x = 0
                    self.cursor_y += 1
                    if self.cursor_y >= self.rows:
                        self._scroll()
                        self.cursor_y = self.rows - 1
            i += 1

    def _scroll(self):
        self.grid.pop(0)
        self.grid.append([' ' for _ in range(self.cols)])

    def _handle_csi(self, params, command):
        def get_param(idx, default=1):
            try:
                # Strip prefix chars like '?' from the string before int()
                p_str = "".join(c for c in params[idx] if c.isdigit())
                if p_str: return int(p_str)
            except: pass
            return default

        if command == 'H' or command == 'f': # Position
            y = get_param(0) - 1
            x = get_param(1) - 1
            self.cursor_y = max(0, min(y, self.rows - 1))
            self.cursor_x = max(0, min(x, self.cols - 1))
        elif command == 'G': # Horizontal Absolute
            self.cursor_x = max(0, min(get_param(0) - 1, self.cols - 1))
        elif command == 'A': # Up
            self.cursor_y = max(0, self.cursor_y - get_param(0))
        elif command == 'B': # Down
            self.cursor_y = min(self.rows - 1, self.cursor_y + get_param(0))
        elif command == 'C': # Forward
            self.cursor_x = min(self.cols - 1, self.cursor_x + get_param(0))
        elif command == 'D': # Backward
            self.cursor_x = max(0, self.cursor_x - get_param(0))
        elif command == 'J': # Erase Display
            mode = get_param(0, 0)
            if mode == 2: self.clear()
        elif command == 'K': # Erase Line
            mode = get_param(0, 0)
            if mode == 0: # To end
                for x in range(self.cursor_x, self.cols): self.grid[self.cursor_y][x] = ' '
            elif mode == 1: # From start
                for x in range(0, min(self.cursor_x + 1, self.cols)): self.grid[self.cursor_y][x] = ' '
            elif mode == 2: # All
                self.grid[self.cursor_y] = [' ' for _ in range(self.cols)]
