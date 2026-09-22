# Mouse Utilities para o Omarchy

Ache o ponteiro, ou torne impossível perdê-lo. São as
[mouse utilities do PowerToys](https://learn.microsoft.com/windows/powertoys/mouse-utilities)
— Find My Mouse, Mouse Highlighter e Mouse Crosshairs — portadas para o
[Omarchy](https://omarchy.org).

*[Read in English](README.md)*

```bash
omarchy-mouse-utils find         # um holofote que some depois que você achou
omarchy-mouse-utils crosshairs   # linhas cruzando o ponteiro, para gravar a tela
omarchy-mouse-utils ring         # um destaque em volta dele
omarchy-mouse-utils off          # desliga o que estiver aparecendo
```

Os três são **atravessáveis por clique**: tudo que está embaixo continua funcionando
enquanto eles estão no ar. Nada é capturado, nada é bloqueado — você segue clicando,
arrastando e digitando com a mira ainda acompanhando você.

## Como funciona, e por que tinha que ser assim

Um overlay no Wayland escolhe: ou recebe os eventos do ponteiro, ou é invisível para
eles. Receber engoliria todo clique; não receber significa que o overlay não enxerga o
ponteiro. Então a posição vem de fora — o `omarchy-mouse-utils track` lê o socket de
IPC do Hyprland e escreve uma linha por movimento, e o overlay segue esse fluxo.

O socket faz diferença. O `hyprctl cursorpos` custa cerca de **25 ms** — criar um
processo, conectar, interpretar — e um holofote que acompanha o ponteiro pergunta
sessenta vezes por segundo. A mesma pergunta direto no socket custa **0,16 ms**, e é
isso que torna a coisa viável.

Só mudanças são enviadas: um ponteiro parado não gera tráfego, então uma mira deixada
ligada durante uma reunião longa não custa nada.

## Instalação

### Arch / Omarchy

```bash
sudo pacman -U omarchy-mouse-utils-*-any.pkg.tar.zst   # dos Releases
omarchy-mouse-utils setup
```

No `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + M", "Achar o ponteiro", "omarchy-mouse-utils find")
o.bind("SUPER + SHIFT + X", "Mira", "omarchy-mouse-utils crosshairs")
```

`crosshairs` e `ring` alternam: o mesmo atalho desliga. O `find` sempre aparece e some
sozinho.

Preferências em `~/.config/omarchy-mouse-utils/config.json`:

```json
{ "colour": "#ff8800", "thickness": 2, "radius": 110, "dim": 0.55, "fade_after": 1200, "hz": 60 }
```

Deixar `colour` vazio segue a cor de destaque do seu tema.

### Em outras distros

`pipx install git+https://github.com/andrebbruno/omarchy-mouse-utils`, com `quickshell`.
O overlay precisa de um compositor wlroots e o rastreador precisa do socket de IPC do
Hyprland.

## Comandos

```
omarchy-mouse-utils              o menu
omarchy-mouse-utils find         o holofote (some depois de um instante)
omarchy-mouse-utils crosshairs   linhas que acompanham o ponteiro
omarchy-mouse-utils ring         um círculo em volta dele
omarchy-mouse-utils off          desliga
omarchy-mouse-utils where        onde está o ponteiro, e em qual monitor
omarchy-mouse-utils track        o fluxo de posições, um "x y" por linha
omarchy-mouse-utils status       o que está no ar e as preferências
```

O `track` é útil por si só — é um fluxo de posição do cursor que qualquer coisa pode ler.

## Desenvolvimento

```bash
python -m pytest tests -q     # 36 testes, sem precisar de compositor
```

O protocolo do socket, a geometria dos monitores (inclusive com escala) e o
estrangulamento do fluxo são Python e testados contra um ponteiro falso; o overlay é QML
e foi exercitado numa área de trabalho real — o holofote, a mira e, mais importante, um
clique chegando na janela de baixo com o overlay no ar.

## Licença

MIT © Andre Bruno
