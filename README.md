# APM Overlay

APM Overlay est une application Python de suivi d’APM en temps réel, pensée pour les joueurs, streamers et créateurs de contenu. Elle affiche un overlay moderne, suit vos actions, propose des profils d’usage, des alertes, un mode focus, des snapshots et une intégration locale pour le stream.

## Fonctionnalités

- Suivi en temps réel de l’APM
- Mesures complémentaires : CPS, DPM
- Overlay moderne et personnalisable
- Profils : Default, FPS, RTS, MOBA, Coaching, Streaming
- Mode focus et mode compact / mini
- Alertes visuelles et sonores
- Historique exportable en CSV
- Snapshots JSON
- API locale et overlay HTML pour OBS / navigateur
- Intégration OBS WebSocket optionnelle

## Prérequis

- Python 3.9+
- Module Python : pynput

Installation :

```bash
pip install pynput
```

## Lancer l’application

Depuis la racine du projet :

```bash
python apm.py
```

Si vous utilisez l’environnement virtuel du projet :

```bash
.venv\Scripts\activate
python apm.py
```

## Structure du projet

- apm.py : point d’entrée principal
- apm_ui.py : interface Tkinter
- apm_events.py : capture des événements clavier/souris
- apm_streaming.py : API locale et overlay HTTP
- apm_config.py : sauvegarde/chargement de la configuration
- apm_stats.py : export CSV et snapshots
- apm_overlay.py : page HTML de l’overlay navigateur

## GitHub / publication

Initialiser le dépôt si nécessaire :

```bash
git init
git add .
git commit -m "Initial commit"
```

Ajouter votre remote GitHub :

```bash
git remote add origin https://github.com/VOTRE_UTILISATEUR/VOTRE_REPO.git
```

Envoyer les changements :

```bash
git push -u origin main
```

Si votre branche est nommée master :

```bash
git push -u origin master
```

## Notes

L’application peut être utilisée comme overlay pour OBS via une source navigateur pointant vers l’URL locale fournie par l’API. Les réglages sont enregistrés dans apm_config.json.
