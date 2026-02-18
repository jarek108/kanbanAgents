import re

class TerminalScreen:
    def __init__(self, cols=120, rows=30):
        self.cols = cols
        self.rows = rows
        self.clear()
        
        # Regex for ANSI escape sequences
        # This matches CSI (Command Sequence Introducer) sequences
        self.ansi_re = re.compile(r'\x1b\[([0-9;?]*)([A-Za-z])')

    def clear(self):
        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.cursor_x = 0
        self.cursor_y = 0

    def get_text(self):
        return "\n".join("".join(row).rstrip() for row in self.grid)

    def get_cursor(self):
        return self.cursor_x, self.cursor_y

    def feed(self, data):
        # Handle simple characters and escape sequences
        i = 0
        while i < len(data):
            char = data[i]
            
            if char == '\x1b':
                match = self.ansi_re.match(data, i)
                if match:
                    params = match.group(1).split(';')
                    command = match.group(2)
                    self._handle_csi(params, command)
                    i += len(match.group(0))
                    continue
                else:
                    # Partial or unknown escape - just skip for now to avoid hang
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
            else:
                # Regular character
                if self.cursor_y < self.rows and self.cursor_x < self.cols:
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
                if idx < len(params) and params[idx]:
                    return int(params[idx])
            except:
                pass
            return default

        if command == 'H' or command == 'f': # Cursor Position
            y = get_param(0) - 1
            x = get_param(1) - 1
            self.cursor_y = max(0, min(y, self.rows - 1))
            self.cursor_x = max(0, min(x, self.cols - 1))
        elif command == 'A': # Cursor Up
            self.cursor_y = max(0, self.cursor_y - get_param(0))
        elif command == 'B': # Cursor Down
            self.cursor_y = min(self.rows - 1, self.cursor_y + get_param(0))
        elif command == 'C': # Cursor Forward
            self.cursor_x = min(self.cols - 1, self.cursor_x + get_param(0))
        elif command == 'D': # Cursor Backward
            self.cursor_x = max(0, self.cursor_x - get_param(0))
        elif command == 'J': # Erase in Display
            mode = get_param(0, 0)
            if mode == 2: # Entire screen
                self.clear()
        elif command == 'K': # Erase in Line
            mode = get_param(0, 0)
            if mode == 0: # From cursor to end of line
                for x in range(self.cursor_x, self.cols):
                    self.grid[self.cursor_y][x] = ' '
            elif mode == 1: # From beginning to cursor
                for x in range(0, self.cursor_x + 1):
                    self.grid[self.cursor_y][x] = ' '
            elif mode == 2: # Entire line
                self.grid[self.cursor_y] = [' ' for _ in range(self.cols)]
        elif command == 'm': # Graphics (Colors)
            pass # We ignore colors for the raw text grid
