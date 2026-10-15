"""Готовит XML-исходники расширения к загрузке в конкретную типовую конфигурацию.

Платформа сверяет у расширения контролируемые свойства с расширяемой конфигурацией:
идентификатор каждого заимствованного объекта (ExtendedConfigurationObject) и режим
совместимости интерфейса. В разных линейках (ERP/УТ и УНФ) у одноимённых объектов БСП
разные идентификаторы, поэтому расширение, собранное в ERP, в УНФ не загружается.

Скрипт копирует расширение и подставляет значения из выгрузки целевой конфигурации
(DumpConfigToFiles, иерархический формат). Выгрузка должна быть свежей: сохранённые
исходники базы могут отставать от её конфигурации.

    python tools/cfe_for_config.py <расширение> <выгрузка конфигурации> <каталог результата>
"""

import re
import shutil
import sys
from pathlib import Path

ADOPTED = "<ObjectBelonging>Adopted</ObjectBelonging>"
EXTENDED = re.compile(r"(<ExtendedConfigurationObject>)[0-9a-f-]+(</ExtendedConfigurationObject>)")
UUID = re.compile(r'<(\w+) uuid="([0-9a-f-]+)">')
INTERFACE = re.compile(r"(<InterfaceCompatibilityMode>)[^<]*(</InterfaceCompatibilityMode>)")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8-sig", newline="")


def main(extension: Path, target: Path, output: Path) -> int:
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(extension, output, ignore=shutil.ignore_patterns("ConfigDumpInfo.xml"))

    missing = []
    changed = 0
    for path in sorted(output.glob("*/*.xml")):
        text = read(path)
        if ADOPTED not in text:
            continue
        relative = path.relative_to(output)
        source = target / relative
        if not source.exists():
            missing.append(str(relative))
            continue
        found = UUID.search(read(source))
        if not found:
            missing.append(f"{relative} (нет uuid)")
            continue
        updated = EXTENDED.sub(lambda m: m.group(1) + found.group(2) + m.group(2), text, count=1)
        if updated != text:
            write(path, updated)
            changed += 1

    root = output / "Configuration.xml"
    mode = INTERFACE.search(read(target / "Configuration.xml"))
    if mode:
        write(root, INTERFACE.sub(lambda m: m.group(1) + mode.group(0)[len(m.group(1)):-len(m.group(2))] + m.group(2),
                                  read(root), count=1))

    print(f"заимствованных объектов обновлено: {changed}")
    print(f"режим интерфейса: {mode.group(0) if mode else 'не найден в выгрузке'}")
    if missing:
        print("в целевой конфигурации нет объектов: " + ", ".join(missing))
        return 2
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
