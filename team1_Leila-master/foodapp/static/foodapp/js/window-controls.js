// Définition de l'interface avec Electron
window.electron = {
    minimize: () => {
        if (window.electron && window.electron.ipcRenderer) {
            window.electron.ipcRenderer.send('minimize-window');
        }
    },
    maximize: () => {
        if (window.electron && window.electron.ipcRenderer) {
            window.electron.ipcRenderer.send('maximize-window');
        }
    },
    close: () => {
        if (window.electron && window.electron.ipcRenderer) {
            window.electron.ipcRenderer.send('close-window');
        }
    }
};

// Gestion du drag de la fenêtre
document.addEventListener('DOMContentLoaded', () => {
    const titlebar = document.querySelector('.titlebar');
    if (titlebar) {
        let isDragging = false;
        let startPos = { x: 0, y: 0 };

        titlebar.addEventListener('mousedown', (e) => {
            if (e.target.closest('.window-controls')) return;
            
            isDragging = true;
            startPos = {
                x: e.clientX,
                y: e.clientY
            };
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startPos.x;
            const deltaY = e.clientY - startPos.y;

            if (window.electron && window.electron.ipcRenderer) {
                window.electron.ipcRenderer.send('move-window', { deltaX, deltaY });
            }

            startPos = {
                x: e.clientX,
                y: e.clientY
            };
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }
}); 