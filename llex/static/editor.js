import { Editor, Node, Mark } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Document from '@tiptap/extension-document';

const ScaffoldMark = Mark.create({
    name: 'scaffold',
    keepOnSplit: false,
    addAttributes() {
        return {
            id: { default: null },
            comment: { default: '' }
        };
    },
    parseHTML() {
        return [{ tag: 'span[data-scaffold]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return ['span', { 
            'data-scaffold': HTMLAttributes.comment,
            'data-scaffold-id': HTMLAttributes.id,
            style: 'background-color: rgba(255, 235, 59, 0.4); border-bottom: 2px dashed #f4b41a; cursor: pointer;'
        }, 0];
    }
});

const Page = Node.create({
    name: 'page',
    group: 'page',
    content: 'block+',
    parseHTML() {
        return [{ tag: 'div.page' }]
    },
    renderHTML({ HTMLAttributes }) {
        return ['div', { class: 'page', ...HTMLAttributes }, 0]
    }
});

const CustomDocument = Document.extend({
    content: 'page+',
});

document.addEventListener('DOMContentLoaded', async () => {

    let initialContent = '<div class="page"><p>Start typing your document...</p></div>';
    try {
        const res = await fetch('/api/load');
        const data = await res.json();
        if (data && data.html) {
            initialContent = data.html;
        }
    } catch(err) {
        console.error('Failed to load document:', err);
    }

    const editor = new Editor({
        element: document.querySelector('#editor'),
        extensions: [
            CustomDocument,
            Page,            ScaffoldMark,            StarterKit.configure({
                document: false,
            }),
            Underline,
            TextAlign.configure({
                types: ['heading', 'paragraph'],
            }),
        ],
        content: initialContent,
        editorProps: {
            transformPastedHTML(html) {
                const temp = document.createElement('div');
                temp.innerHTML = html;
                const pages = temp.querySelectorAll('.page');
                pages.forEach(p => {
                    while (p.firstChild) p.parentNode.insertBefore(p.firstChild, p);
                    p.remove();
                });
                return temp.innerHTML;
            },
            handlePaste: (view, event, slice) => {
                if (slice.content.size > 8000) {
                    const confirmPaste = confirm("You are pasting a large amount of text (" + slice.content.size + " chars). This may cause a 'ripple' effect as blocks are reflowed into pages. Proceed?");
                    if (!confirmPaste) {
                        return true; // handled, meaning do not paste
                    }
                }
                return false; // let TipTap handle paste
            }
        },
        onUpdate: ({ editor }) => {
            updateFormatState();
            generateDocumentOutline();

            // Pagination block movement engine
            requestAnimationFrame(() => {
                const domPages = document.querySelectorAll('.page');
                let offset = 0;
                for (let i = 0; i < domPages.length; i++) {
                    const domPage = domPages[i];
                    const pageNode = editor.state.doc.child(i);
                    
                    if (domPage.scrollHeight > domPage.clientHeight + 1) { // +1 for layout tolerance
                        try {
                            // Don't reflow if it's the only block on the page
                            if (pageNode.childCount <= 1) break;
                            
                            const lastChild = pageNode.lastChild;
                            if (!lastChild) break;
                            
                            // Calculate ProseMirror offsets based on document structure
                            const lastChildStart = offset + pageNode.nodeSize - lastChild.nodeSize - 1; 

                            editor.commands.command(({ tr, dispatch }) => {
                                if (dispatch) {
                                    // Extract block
                                    const blockSlice = tr.doc.slice(lastChildStart, lastChildStart + lastChild.nodeSize);
                                    const nextPageIndex = i + 1;

                                    if (nextPageIndex < domPages.length) {
                                        // Next page exists, prepend block
                                        const nextPos = offset + pageNode.nodeSize;
                                        tr.insert(nextPos + 1, blockSlice.content);
                                        tr.delete(lastChildStart, lastChildStart + lastChild.nodeSize);
                                    } else {
                                        // Create a new page with the block
                                        const newPage = editor.schema.nodes.page.create(null, blockSlice.content.content);
                                        tr.insert(offset + pageNode.nodeSize, newPage);
                                        tr.delete(lastChildStart, lastChildStart + lastChild.nodeSize);
                                    }
                                }
                                return true;
                            });
                            
                            // Handle one overflow block per frame to create the "ripple"
                            break;
                        } catch (e) {
                            console.error('Pagination reflow error:', e);
                        }
                    }
                    offset += pageNode.nodeSize;
                }
            });
        },
        onSelectionUpdate: ({ editor }) => {
            updateFormatState();
        }
    });

    const menuSave = document.getElementById('menu-save');
    const menuSaveAs = document.getElementById('menu-save-as');

    // Save
    if(menuSave) menuSave.addEventListener('click', async () => {
        const btnText = menuSave.innerText;
        menuSave.innerText = 'Saving...';
        try {
            await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ html: editor.getHTML() })
            });
            menuSave.innerText = 'Saved!';
            setTimeout(() => { menuSave.innerText = btnText; }, 2000);
        } catch(err) {
            menuSave.innerText = 'Error!';
            setTimeout(() => { menuSave.innerText = btnText; }, 2000);
        }
    });

    // Save As
    if(menuSaveAs) menuSaveAs.addEventListener('click', async () => {
        const btnText = menuSaveAs.innerText;
        menuSaveAs.innerText = 'Saving...';
        try {
            await fetch('/api/save_as', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ html: editor.getHTML() })
            });
            menuSaveAs.innerText = 'Saved!';
            setTimeout(() => { menuSaveAs.innerText = btnText; }, 2000);
        } catch(err) {
            menuSaveAs.innerText = 'Error!';
            setTimeout(() => { menuSaveAs.innerText = btnText; }, 2000);
        }
    });

    const btnUndo = document.getElementById('btn-undo');
    const btnRedo = document.getElementById('btn-redo');
    const btnBold = document.getElementById('btn-bold');
    const btnItalic = document.getElementById('btn-italic');
    const btnUnderline = document.getElementById('btn-underline');
    const btnStrikethrough = document.getElementById('btn-strikethrough');
    const btnAlignLeft = document.getElementById('btn-align-left');
    const btnAlignCenter = document.getElementById('btn-align-center');
    const btnAlignRight = document.getElementById('btn-align-right');
    const btnAlignJustify = document.getElementById('btn-align-justify');
    const btnBullet = document.getElementById('btn-bullet');
    const btnNumber = document.getElementById('btn-number');
    const styleDropdown = document.getElementById('style-dropdown');

    if(btnUndo) btnUndo.addEventListener('click', () => editor.chain().focus().undo().run());
    if(btnRedo) btnRedo.addEventListener('click', () => editor.chain().focus().redo().run());
    if(btnBold) btnBold.addEventListener('click', () => editor.chain().focus().toggleBold().run());
    if(btnItalic) btnItalic.addEventListener('click', () => editor.chain().focus().toggleItalic().run());
    if(btnUnderline) btnUnderline.addEventListener('click', () => editor.chain().focus().toggleUnderline().run());
    if(btnStrikethrough) btnStrikethrough.addEventListener('click', () => editor.chain().focus().toggleStrike().run());
    
    if(btnAlignLeft) btnAlignLeft.addEventListener('click', () => editor.chain().focus().setTextAlign('left').run());
    if(btnAlignCenter) btnAlignCenter.addEventListener('click', () => editor.chain().focus().setTextAlign('center').run());
    if(btnAlignRight) btnAlignRight.addEventListener('click', () => editor.chain().focus().setTextAlign('right').run());
    if(btnAlignJustify) btnAlignJustify.addEventListener('click', () => editor.chain().focus().setTextAlign('justify').run());

    if(styleDropdown) styleDropdown.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val === 'p') {
            editor.chain().focus().setParagraph().run();
        } else if (val.startsWith('h')) {
            const level = parseInt(val.charAt(1));
            editor.chain().focus().setHeading({ level: level }).run();
        }
    });

    if(btnBullet) btnBullet.addEventListener('click', () => editor.chain().focus().toggleBulletList().run());
    if(btnNumber) btnNumber.addEventListener('click', () => editor.chain().focus().toggleOrderedList().run());

    // Sidebar Toggle
    const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
    const sidebar = document.getElementById('sidebar');
    if(btnToggleSidebar && sidebar) {
        btnToggleSidebar.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (sidebar.classList.contains('open')) {
                btnToggleSidebar.classList.add('active');
            } else {
                btnToggleSidebar.classList.remove('active');
            }
        });
    }

    // Context Menu Logic
    const contextMenu = document.getElementById('context-menu');
    const contextMenuStandard = document.getElementById('context-menu-standard');
    const editorContainer = document.querySelector('.tiptap') || document.querySelector('#editor');

    if (editorContainer && contextMenu) {
        // Show custom menu on right-click within the editor container
        editorContainer.addEventListener('contextmenu', (e) => {
            // Only handle context menu if clicking inside a page
            if (!e.target.closest('.page')) return;
            
            e.preventDefault();

            const hasSelection = !editor.state.selection.empty;

            if (hasSelection) {
                // Both menus visible when text is selected
                contextMenu.style.display = 'flex'; // mini toolbar
                contextMenu.style.left = `${e.pageX}px`;
                contextMenu.style.top = `${e.pageY}px`;

                if (contextMenuStandard) {
                    contextMenuStandard.style.display = 'flex';
                    // Position it slightly below the mini toolbar
                    contextMenuStandard.style.left = `${e.pageX}px`;
                    contextMenuStandard.style.top = `${e.pageY + contextMenu.offsetHeight + 4}px`;
                }

                // Sync current editor state with mini toolbar
                const ffSelect = contextMenu.querySelector('.mt-font-family');
                if(ffSelect && editor.getAttributes('textStyle').fontFamily) {
                    ffSelect.value = editor.getAttributes('textStyle').fontFamily;
                }
                const activeMarks = editor.state.selection.$from.marks().map(m => m.type.name);
                contextMenu.querySelectorAll('.mt-btn').forEach(btn => {
                    const action = btn.getAttribute('data-action');
                    if (activeMarks.includes(action)) btn.classList.add('active');
                    else btn.classList.remove('active');
                });
            } else {
                // Only standard menu when no text is selected
                contextMenu.style.display = 'none';
                if (contextMenuStandard) {
                    contextMenuStandard.style.display = 'flex';
                    contextMenuStandard.style.left = `${e.pageX}px`;
                    contextMenuStandard.style.top = `${e.pageY}px`;
                }
            }
        });

        // Hide menus when user starts typing or navigating
        editor.view.dom.addEventListener('keydown', () => {
            contextMenu.style.display = 'none';
            if (contextMenuStandard) contextMenuStandard.style.display = 'none';
        });

        // Hide context menu on normal click anywhere
        document.addEventListener('click', (e) => {
            if (e.target.closest('#context-menu') || e.target.closest('#context-menu-standard')) return;
            contextMenu.style.display = 'none';
            if (contextMenuStandard) contextMenuStandard.style.display = 'none';
        });

        if (contextMenuStandard) {
            contextMenuStandard.addEventListener('click', async (e) => {
                const item = e.target.closest('[data-action]');
                if (!item) return;

                const action = item.getAttribute('data-action');
                if (action === 'cut') {
                    document.execCommand('cut');
                } else if (action === 'copy') {
                    document.execCommand('copy');
                } else if (action === 'paste') {
                    try {
                        const text = await navigator.clipboard.readText();
                        editor.chain().focus().insertContent(text).run();
                    } catch (err) {
                        alert('Please use Ctrl+V / Cmd+V to paste due to browser security restrictions.');
                    }
                }
                contextMenuStandard.style.display = 'none';
                contextMenu.style.display = 'none';
            });
        }

        // Context Menu Actions (Buttons)
        contextMenu.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn || btn.tagName === 'SELECT') return;

            const action = btn.getAttribute('data-action');
            if (!action) return;

            e.preventDefault();

            switch(action) {
                case 'bold': editor.chain().focus().toggleBold().run(); break;
                case 'italic': editor.chain().focus().toggleItalic().run(); break;
                case 'underline': editor.chain().focus().toggleUnderline().run(); break;
                case 'increase-font': 
                    // Needs custom logic or just fallback to generic
                    break;
                case 'decrease-font': 
                    break;
                case 'clear-format': editor.chain().focus().unsetAllMarks().clearNodes().run(); break;
                case 'bullet-list': editor.chain().focus().toggleBulletList().run(); break;
                case 'ordered-list': editor.chain().focus().toggleOrderedList().run(); break;
                case 'styles': 
                    // Could open another sub-menu or just default to paragraph
                    break;
                case 'add-scaffold':
                    const comment = prompt("Enter scaffold instruction/comment:");
                    if (comment) {
                        const id = String(Date.now());
                        editor.view.dispatch(editor.state.tr.addMark(
                            editor.state.selection.from, 
                            editor.state.selection.to, 
                            editor.schema.marks.scaffold.create({ id, comment })
                        ));
                    }
                    contextMenu.style.display = 'none';
                    if (contextMenuStandard) contextMenuStandard.style.display = 'none';
                    break;
                // Add highlight/font color popups logic or defaults here depending on extensions
            }
        });

        // Context Menu Actions (Dropdowns)
        contextMenu.addEventListener('change', (e) => {
            const select = e.target.closest('select[data-action]');
            if (!select) return;

            const action = select.getAttribute('data-action');
            if (action === 'font-family') {
                editor.chain().focus().setFontFamily(select.value).run();
            } else if (action === 'font-size') {
                // Note: fontSize extension needs to be active in editor props
                // editor.chain().focus().setFontSize(select.value).run();
            }
        });
    }

    let outlineTimeout;
    function generateDocumentOutline() {
        if (outlineTimeout) clearTimeout(outlineTimeout);
        outlineTimeout = setTimeout(() => {
            const outlineContainer = document.getElementById('document-outline');
            if (!outlineContainer) return;
            
            const items = [];
            // Parse document looking for semantic headings
            editor.state.doc.descendants((node, pos) => {
                if (node.type.name === 'heading') {
                    const level = node.attrs.level;
                    // H1 = Title, H2 = Subtitle (per your CSS mapping).
                    // Google Docs outline only shows Headings, not titles
                    if (level >= 3) {
                        items.push({ text: node.textContent, level: level, pos: pos });
                    }
                }
            });
            
            outlineContainer.innerHTML = '';
            if (items.length === 0) {
                outlineContainer.innerHTML = '<div style="padding: 10px;">Add Headings (Format > Styles) to see outline</div>';
                return;
            }
            
            items.forEach(item => {
                const div = document.createElement('div');
                // visual indent mapping: level 3 = indent 0, level 4 = indent 10, etc
                const indent = (item.level - 3) * 12; 
                div.style.paddingLeft = indent + 'px';
                div.style.paddingTop = '6px';
                div.style.paddingBottom = '6px';
                div.style.cursor = 'pointer';
                div.style.whiteSpace = 'nowrap';
                div.style.overflow = 'hidden';
                div.style.textOverflow = 'ellipsis';
                
                div.innerText = item.text || 'Empty heading';
                
                div.onmouseover = () => div.style.color = 'white';
                div.onmouseout = () => div.style.color = '#aaa';
                
                // Live anchoring navigation!
                div.onclick = () => {
                    editor.chain().focus().setTextSelection(item.pos).scrollIntoView().run();
                };
                outlineContainer.appendChild(div);
            });
        }, 500);
    }

    function updateFormatState() {
        if(btnBold) {
            if (editor.isActive('bold')) btnBold.classList.add('active');
            else btnBold.classList.remove('active');
        }
        if(btnItalic) {
            if (editor.isActive('italic')) btnItalic.classList.add('active');
            else btnItalic.classList.remove('active');
        }
        if(btnUnderline) {
            if (editor.isActive('underline')) btnUnderline.classList.add('active');
            else btnUnderline.classList.remove('active');
        }
        if(btnStrikethrough) {
            if (editor.isActive('strike')) btnStrikethrough.classList.add('active');
            else btnStrikethrough.classList.remove('active');
        }
        
        if(btnAlignLeft) {
            if (editor.isActive({ textAlign: 'left' })) btnAlignLeft.classList.add('active'); 
            else btnAlignLeft.classList.remove('active');
        }
        if(btnAlignCenter) {
            if (editor.isActive({ textAlign: 'center' })) btnAlignCenter.classList.add('active'); 
            else btnAlignCenter.classList.remove('active');
        }
        if(btnAlignRight) {
            if (editor.isActive({ textAlign: 'right' })) btnAlignRight.classList.add('active'); 
            else btnAlignRight.classList.remove('active');
        }
        if(btnAlignJustify) {
            if (editor.isActive({ textAlign: 'justify' })) btnAlignJustify.classList.add('active'); 
            else btnAlignJustify.classList.remove('active');
        }

        if(styleDropdown) {
            let currentStyle = 'p';
            for (let i = 1; i <= 6; i++) {
                if (editor.isActive('heading', { level: i })) {
                    currentStyle = 'h' + i;
                    break;
                }
            }
            styleDropdown.value = currentStyle;
        }

        if(btnBullet) {
            if (editor.isActive('bulletList')) btnBullet.classList.add('active');
            else btnBullet.classList.remove('active');
        }
        if(btnNumber) {
            if (editor.isActive('orderedList')) btnNumber.classList.add('active');
            else btnNumber.classList.remove('active');
        }
    }
});
document.addEventListener('DOMContentLoaded', () => {
    // Settings Logic
    const menuSettings = document.getElementById('menu-settings');
    const settingsModal = document.getElementById('settings-modal');
    const btnCancel = document.getElementById('btn-settings-cancel');
    const btnSave = document.getElementById('btn-settings-save');
    
    // Inputs
    const mTop = document.getElementById('margin-top');
    const mRight = document.getElementById('margin-right');
    const mBottom = document.getElementById('margin-bottom');
    const mLeft = document.getElementById('margin-left');
    const tBg = document.getElementById('theme-bg');
    const tPaper = document.getElementById('theme-paper');
    const tText = document.getElementById('theme-text');
    const tRibbon = document.getElementById('theme-ribbon');
    const tBorder = document.getElementById('theme-border');

    function loadSettings() {
        const s = JSON.parse(localStorage.getItem('llex-settings') || '{}');
        mTop.value = s.marginTop || "1";
        mRight.value = s.marginRight || "1";
        mBottom.value = s.marginBottom || "1";
        mLeft.value = s.marginLeft || "1";
        
        tBg.value = s.themeBg || "#f0f0f0";
        tPaper.value = s.themePaper || "#ffffff";
        tText.value = s.themeText || "#000000";
        tRibbon.value = s.themeRibbon || "#2b2b2b";
        tBorder.value = s.themeBorder || "#444444";
        applySettingsToDOM();
    }

    function applySettingsToDOM() {
        const root = document.documentElement;
        root.style.setProperty('--bg-dark', tBg.value);
        root.style.setProperty('--paper-bg', tPaper.value);
        root.style.setProperty('--ribbon-bg', tRibbon.value);
        root.style.setProperty('--text-color', tText.value);
        root.style.setProperty('--border-color', tBorder.value);

        // margins
        root.style.setProperty('--margin-top', (mTop.value * 96) + 'px');
        root.style.setProperty('--margin-right', (mRight.value * 96) + 'px');
        root.style.setProperty('--margin-bottom', (mBottom.value * 96) + 'px');
        root.style.setProperty('--margin-left', (mLeft.value * 96) + 'px');
    }

    if (btnSave) {
        btnSave.addEventListener('click', () => {
            const s = {
                marginTop: mTop.value,
                marginRight: mRight.value,
                marginBottom: mBottom.value,
                marginLeft: mLeft.value,
                themeBg: tBg.value,
                themePaper: tPaper.value,
                themeText: tText.value,
                themeRibbon: tRibbon.value,
                themeBorder: tBorder.value
            };
            localStorage.setItem('llex-settings', JSON.stringify(s));
            applySettingsToDOM();
            settingsModal.style.display = 'none';
        });
    }

    // Call on start
    loadSettings();
    
    // Apply font-family
    const fontFamilyDropdown = document.getElementById('font-family');
    fontFamilyDropdown.addEventListener('change', (e) => {
        // Tiptap doesn't natively support font-family without FontFamily extension 
        // Let's add inline style to entire text or use a basic execCommand as a quick workaround 
        // for custom themes. Since we only have starter-kit, we apply to whole document for this rapid implementation:
        const editorDom = document.querySelector('.tiptap');
        if (editorDom) {
            editorDom.style.fontFamily = e.target.value;
        }
    });

    const btnExecuteScaffolds = document.getElementById('btn-execute-scaffolds');
    if (btnExecuteScaffolds) {
        btnExecuteScaffolds.addEventListener('click', async () => {
            const scaffoldsHTML = Array.from(document.querySelectorAll('span[data-scaffold]'));
            if (scaffoldsHTML.length === 0) {
                alert("No scaffolds found! Highlight some text, right click and hit 'Scaffold' to add some.");
                return;   
            }

            // Extract scaffolds from the actual TipTap state to get their positions
            let payloadScaffolds = [];
            editor.state.doc.descendants((node, pos) => {
                const mark = node.marks.find(m => m.type.name === 'scaffold');
                if (mark && mark.attrs.id) {
                    // Group adjacent text nodes that share the same scaffold ID
                    const existing = payloadScaffolds.find(s => s.id === mark.attrs.id);
                    if (existing) {
                        existing.text += node.textContent;
                        existing.end = pos + node.nodeSize;
                    } else {
                        payloadScaffolds.push({
                            id: Number(mark.attrs.id), // Ensure it matches backend Pydantic validator integer
                            instruction: mark.attrs.comment,
                            text: node.textContent,
                            start: pos,
                            end: pos + node.nodeSize
                        });
                    }
                }
            });

            if (payloadScaffolds.length === 0) return;

            btnExecuteScaffolds.innerHTML = "Processing...";
            btnExecuteScaffolds.disabled = true;

            try {
                // Call the backend AI endpoint
                const res = await fetch('/api/scaffold', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scaffolds: payloadScaffolds })
                });
                
                const data = await res.json();
                
                if (data.status === 'success') {
                    // Update document. We apply updates from last to first so positions don't shift.
                    const results = data.results;
                    
                    // Match payloads back to their computed ranges from end to start
                    // Note: If multiple nodes are returned, just iterate them correctly.
                    payloadScaffolds.sort((a, b) => b.start - a.start);
                    
                    let tr = editor.state.tr;
                    payloadScaffolds.forEach(scaffold => {
                        const resultObj = results.find(r => r.id === scaffold.id);
                        if (resultObj) {
                            // First, remove the mark entirely from that chunk
                            tr.removeMark(scaffold.start, scaffold.end, editor.schema.marks.scaffold);
                            
                            // Replace range gracefully with new text (which may contain newlines)
                            tr.insertText(resultObj.text, scaffold.start, scaffold.end);
                        }
                    });
                    
                    editor.view.dispatch(tr);
                } else {
                    alert("Error processing scaffolds: " + data.message);
                }
            } catch (err) {
                console.error(err);
                alert("Failed to communicate with API.");
            } finally {
                btnExecuteScaffolds.innerHTML = "Execute Scaffolds";
                btnExecuteScaffolds.disabled = false;
            }
        });
    }
});


