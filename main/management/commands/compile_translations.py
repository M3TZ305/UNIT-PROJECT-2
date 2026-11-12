"""Compile the project's UTF-8 PO catalogue using the standard library."""
import ast
import struct
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def compile_po(path):
    messages = {}
    key = value = None
    field = None
    def finish():
        if key is not None and value is not None:
            messages[key] = value
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith('msgid '):
            finish()
            key, value, field = ast.literal_eval(line[6:]), None, 'key'
        elif line.startswith('msgstr '):
            value, field = ast.literal_eval(line[7:]), 'value'
        elif line.startswith('"'):
            if field == 'key':
                key += ast.literal_eval(line)
            elif field == 'value':
                value += ast.literal_eval(line)
    finish()
    keys = sorted(messages)
    ids, values, offsets = b'', b'', []
    for key in keys:
        raw_key, raw_value = key.encode('utf-8'), messages[key].encode('utf-8')
        offsets.append((len(raw_key), len(ids), len(raw_value), len(values)))
        ids += raw_key + b'\0'
        values += raw_value + b'\0'
    count = len(keys)
    id_base = 28 + count * 16
    value_base = id_base + len(ids)
    blob = struct.pack('<7I', 0x950412de, 0, count, 28, 28 + 8 * count, 0, 0)
    blob += b''.join(struct.pack('<2I', a, id_base + b) for a, b, c, d in offsets)
    blob += b''.join(struct.pack('<2I', c, value_base + d) for a, b, c, d in offsets)
    path.with_suffix('.mo').write_bytes(blob + ids + values)
    return count


class Command(BaseCommand):
    help = 'Compile locale/en/LC_MESSAGES/django.po without a system gettext installation.'

    def handle(self, *args, **options):
        path = settings.BASE_DIR / 'locale/en/LC_MESSAGES/django.po'
        try:
            count = compile_po(path)
        except (OSError, SyntaxError, ValueError) as error:
            raise CommandError('Invalid translation catalogue: ' + str(error)) from None
        self.stdout.write(f'Compiled {count} English messages. Restart the server after editing translations.')
