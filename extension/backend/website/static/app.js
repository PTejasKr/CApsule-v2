document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('capsule_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    // Theme Toggle Logic
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        if (currentTheme === 'light') {
            document.body.classList.add('light-mode');
            themeToggle.checked = false; // false = SUN = light mode
        } else {
            themeToggle.checked = true; // true = MOON = dark mode
        }

        themeToggle.addEventListener('change', (e) => {
            if (e.target.checked) {
                // checked = true means Night/Moon
                document.body.classList.remove('light-mode');
                localStorage.setItem('theme', 'dark');
            } else {
                // checked = false means Day/Sun
                document.body.classList.add('light-mode');
                localStorage.setItem('theme', 'light');
            }
        });
    }

    function parseJwt(token) {
        try {
            let base64Url = token.split('.')[1];
            let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            while (base64.length % 4) {
                base64 += '=';
            }
            let jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            return null;
        }
    }

    const user = parseJwt(token);
    if (!user) {
        localStorage.removeItem('capsule_token');
        window.location.href = '/';
        return;
    }

    document.getElementById('user-name').textContent = user.github_username || 'Unknown';
    document.getElementById('user-role').textContent = user.global_role ? user.global_role.replace('_', ' ') : 'USER';
    document.getElementById('user-role').style.display = 'inline-block';

    if (user.global_role === 'super_admin') {
        document.getElementById('nav-teams').style.display = 'block';
        document.getElementById('nav-repositories').style.display = 'block';
        document.getElementById('nav-superadmin').style.display = 'block';
    } else if (user.global_role === 'lead') {
        document.getElementById('nav-teams').style.display = 'block';
        document.getElementById('nav-repositories').style.display = 'block';
    }

    const links = document.querySelectorAll('.nav-menu a');
    const viewTitle = document.getElementById('current-view-title');
    const container = document.getElementById('view-container');

    function renderView(view) {
        links.forEach(l => l.classList.remove('active'));
        const activeLink = document.querySelector(`[data-view="${view}"]`);
        if (activeLink) activeLink.classList.add('active');

        switch(view) {
            case 'home':
                viewTitle.textContent = "Home";
                container.innerHTML = `<div class="card">
                    <h2>Welcome to Capsule</h2>
                    <p>Select an option from the sidebar to manage your workspace.</p>
                </div>`;
                break;
            case 'teams':
                viewTitle.textContent = "Teams & Projects";
                fetchTeams();
                break;
            case 'repositories':
                viewTitle.textContent = "Repositories";
                fetchRepositories();
                break;
            case 'analyses':
                viewTitle.textContent = "PR Analyses";
                fetchAnalyses();
                break;
            case 'superadmin':
                viewTitle.textContent = "Super Admin Dashboard";
                fetchSuperAdmin();
                break;
            case 'settings':
                viewTitle.textContent = "Settings (Rules & BRD)";
                fetchSettings();
                break;
            default:
                container.innerHTML = `<p>View not found.</p>`;
        }
    }

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            renderView(e.target.dataset.view);
        });
    });

    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('capsule_token');
        window.location.href = '/';
    });

    async function apiFetch(endpoint, options = {}) {
        const loader = document.getElementById('capsule-loader');
        if (loader) {
            loader.classList.remove('complete');
            loader.classList.add('loading');
        }
        
        try {
            const res = await fetch(`/api${endpoint}`, {
                ...options,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            if (res.status === 401) {
                localStorage.removeItem('capsule_token');
                window.location.href = '/';
                throw new Error("Unauthorized");
            }
            return res;
        } finally {
            if (loader) {
                loader.classList.remove('loading');
                loader.classList.add('complete');
                setTimeout(() => {
                    loader.classList.remove('complete');
                }, 2000);
            }
        }
    }

    async function fetchTeams() {
        container.innerHTML = '<p>Loading teams...</p>';
        try {
            const res = await apiFetch('/teams');
            const data = await res.json();
            
            let html = `
                <div class="card" style="margin-bottom: 20px;">
                    <h3>Create Team (Admin/Lead)</h3>
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <input type="text" id="team-name" placeholder="Team Name" class="form-input" style="flex: 1; padding: 10px; border-radius: 0; background: transparent; color: var(--text);">
                        <button id="create-team-btn" class="btn primary-btn">Create</button>
                    </div>
                </div>
                <div class="card">
                    <h3>All Teams</h3>
                    <div class="table-container"><table><tr><th>ID</th><th>Name</th><th>Actions</th></tr>
            `;
            
            if (data.teams && data.teams.length > 0) {
                data.teams.forEach(t => {
                    html += `<tr>
                        <td>${t.id}</td>
                        <td>${t.name}</td>
                        <td><button class="btn" onclick="manageTeam(${t.id}, '${t.name}')">Manage Team</button></td>
                    </tr>`;
                });
            } else {
                html += '<tr><td colspan="3">No teams found.</td></tr>';
            }
            html += '</table></div></div>';
            container.innerHTML = html;
            
            const createBtn = document.getElementById('create-team-btn');
            if (createBtn) {
                createBtn.addEventListener('click', async () => {
                    const name = document.getElementById('team-name').value;
                    if (!name) return;
                    try {
                        await apiFetch('/teams', {
                            method: 'POST',
                            body: JSON.stringify({ name: name, created_by: 1 })
                        });
                        fetchTeams();
                    } catch (e) {
                        alert("Failed to create team.");
                    }
                });
            }
        } catch (e) {
            container.innerHTML = `<p class="error">Failed to load teams: ${e.message}</p>`;
        }
    }

    window.manageTeam = async function(teamId, teamName) {
        viewTitle.textContent = `Manage Team: ${teamName}`;
        container.innerHTML = '<p>Loading team details...</p>';
        try {
            const [membersRes, projectsRes] = await Promise.all([
                apiFetch(`/teams/${teamId}/members`),
                apiFetch(`/teams/${teamId}/projects`)
            ]);
            
            const membersData = await membersRes.json();
            const projectsData = await projectsRes.json();
            
            let html = `
                <button class="btn" style="margin-bottom: 1rem;" onclick="renderView('teams')">← Back to Teams</button>
                
                <div style="display: flex; gap: 20px;">
                    <div class="card" style="flex: 1;">
                        <h3>Team Members</h3>
                        <div class="table-container" style="margin-bottom: 15px;">
                            <table><tr><th>Name</th><th>Role</th></tr>
                            ${(membersData.members || []).length > 0 ? membersData.members.map(m => `<tr><td>${m.name}</td><td>${m.role}</td></tr>`).join('') : '<tr><td colspan="2">No members.</td></tr>'}
                            </table>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <input type="number" id="add-member-id" placeholder="Profile ID" class="form-input" style="flex: 1;">
                            <input type="text" id="add-member-role" placeholder="Role (e.g. member)" value="member" class="form-input" style="flex: 1;">
                            <button id="add-member-btn" class="btn">Add Member</button>
                        </div>
                    </div>
                    
                    <div class="card" style="flex: 1;">
                        <h3>Mapped Repositories</h3>
                        <div class="table-container" style="margin-bottom: 15px;">
                            <table><tr><th>Repository</th><th>Mapped At</th></tr>
                            ${(projectsData.projects || []).length > 0 ? projectsData.projects.map(p => `<tr><td>${p.source_repo}</td><td>${new Date(p.created_at).toLocaleDateString()}</td></tr>`).join('') : '<tr><td colspan="2">No mapped repositories.</td></tr>'}
                            </table>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="add-repo-name" placeholder="owner/repo" class="form-input" style="flex: 1;">
                            <button id="add-repo-btn" class="btn">Map Repository</button>
                        </div>
                    </div>
                </div>
            `;
            
            container.innerHTML = html;
            
            document.getElementById('add-member-btn').addEventListener('click', async () => {
                const pid = document.getElementById('add-member-id').value;
                const role = document.getElementById('add-member-role').value;
                if (!pid) return;
                try {
                    await apiFetch(`/teams/${teamId}/members`, {
                        method: 'POST',
                        body: JSON.stringify({ profile_id: parseInt(pid), role: role })
                    });
                    manageTeam(teamId, teamName);
                } catch (e) { alert("Failed to add member."); }
            });
            
            document.getElementById('add-repo-btn').addEventListener('click', async () => {
                const repo = document.getElementById('add-repo-name').value;
                if (!repo) return;
                try {
                    await apiFetch(`/teams/${teamId}/projects`, {
                        method: 'POST',
                        body: JSON.stringify({ source_repo: repo })
                    });
                    manageTeam(teamId, teamName);
                } catch (e) { alert("Failed to map repository."); }
            });
            
        } catch (e) {
            container.innerHTML = `<p class="error">Failed to load team details: ${e.message}</p>`;
        }
    };

    async function fetchRepositories() {
        container.innerHTML = '<p>Loading repositories...</p>';
        try {
            // Using existing profiles endpoint
            const res = await apiFetch('/profiles/');
            const data = await res.json();
            
            let html = `
                <div class="card" style="margin-bottom: 20px;">
                    <h3>Map Repository</h3>
                    <div style="display: flex; gap: 10px; margin-top: 15px; align-items: center;">
                        <input type="text" id="map-repo-input" placeholder="owner/repo" class="form-input" style="flex: 1; padding: 10px; border-radius: 0; border: 1px solid var(--border); background: transparent; color: var(--text);">
                        <select id="map-profile-select" class="form-input" style="flex: 1; padding: 10px; border-radius: 0; border: 1px solid var(--border); background: var(--bg); color: var(--text);">
                            <option value="">Select Profile</option>
            `;
            
            if (data && data.length > 0) {
                data.forEach(p => {
                    html += `<option value="${p.id}">${p.name} (${p.ai_model})</option>`;
                });
            }
            
            html += `
                        </select>
                        <button id="map-repo-btn" class="btn primary-btn" style="padding: 10px 20px; border-radius: 0;">Map</button>
                    </div>
                </div>
                <div class="table-container"><table><tr><th>Profile / Repo</th><th>AI Model</th></tr>
            `;

            if (data && data.length > 0) {
                data.forEach(p => {
                    html += `<tr>
                        <td>${p.source_repo || 'Not mapped'}</td>
                        <td>${p.ai_model}</td>
                    </tr>`;
                });
            } else {
                html += '<tr><td colspan="2">No repositories mapped.</td></tr>';
            }
            html += '</table></div>';
            container.innerHTML = html;
            
            // Add event listener for mapping
            const mapBtn = document.getElementById('map-repo-btn');
            if (mapBtn) {
                mapBtn.addEventListener('click', async () => {
                    const repoInput = document.getElementById('map-repo-input').value;
                    const profileId = document.getElementById('map-profile-select').value;
                    
                    if (!repoInput || !profileId) {
                        alert("Please provide both repository and profile.");
                        return;
                    }
                    
                    mapBtn.textContent = 'Mapping...';
                    mapBtn.disabled = true;
                    
                    try {
                        const mapRes = await apiFetch('/profiles/mappings', {
                            method: 'POST',
                            body: JSON.stringify({
                                source_repo: repoInput,
                                profile_id: parseInt(profileId, 10)
                            })
                        });
                        
                        if (mapRes.ok) {
                            try {
                                const setupRes = await apiFetch('/setup-repository', {
                                    method: 'POST',
                                    body: JSON.stringify({
                                        repo: repoInput,
                                        callback_url: window.location.origin
                                    })
                                });
                                if (setupRes.ok) {
                                    alert("Repository mapped and automated webhook configured successfully!");
                                } else {
                                    const errData = await setupRes.json();
                                    alert("Repository mapped, but automated setup failed: " + (errData.detail || "Unknown error"));
                                }
                            } catch (setupErr) {
                                alert("Repository mapped, but automated setup encountered an error.");
                            }
                            fetchRepositories(); // Reload view
                        } else {
                            const errData = await mapRes.json();
                            alert("Failed to map repository: " + (errData.detail || "Unknown error"));
                        }
                    } catch (err) {
                        alert("Failed to map repository.");
                    } finally {
                        mapBtn.textContent = 'Map';
                        mapBtn.disabled = false;
                    }
                });
            }
            
        } catch (e) {
            container.innerHTML = `<p class="error">Failed to load repositories</p>`;
        }
    }

    window.currentAnalyses = [];

    window.showDetails = function(index) {
        const item = window.currentAnalyses[index];
        if (!item) return;
        
        let riskColor = item.risk_level === 'High' ? '#ef4444' : (item.risk_level === 'Medium' ? '#f59e0b' : '#22c55e');
        
        let detailHtml = `<div class="card">
            <button class="btn" style="margin-bottom: 1rem;" onclick="renderView('analyses')">← Back to List</button>
            <h2>PR #${item.pr_number} - ${item.title || 'Untitled'}</h2>
            
            <div class="tabs" style="display:flex; gap: 10px; margin-bottom: 15px; border-bottom: 1px solid var(--border); padding-bottom: 10px;">
                <button class="tab-btn active btn" onclick="switchTab('summary')" id="tab-summary">Summary</button>
                <button class="tab-btn btn" onclick="switchTab('diff', ${item.pr_number}, '${item.repo.replace(/'/g, "\\'")}')" id="tab-diff">Raw Diff</button>
            </div>
            
            <div id="content-summary">
                <div style="display:flex; gap:10px; margin-bottom: 1rem;">
                   <span class="badge" style="background: rgba(255,255,255,0.1)">Risk: <strong style="color:${riskColor}">${item.risk_level || 'Low'}</strong></span>
                   <span class="badge" style="background: rgba(255,255,255,0.1)">BRD Alignment: <strong>${item.brd_alignment_score || 0}/100</strong></span>
                </div>
                <p><strong>Summary:</strong></p>
                <pre style="white-space: pre-wrap; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; margin-bottom: 1rem;">${item.summary}</pre>
        `;
        
        if (item.mermaid_graph) {
            detailHtml += `<p><strong>Workflow Impact:</strong></p>
            <div class="mermaid" style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-top:10px;">
                ${item.mermaid_graph}
            </div>`;
        }
        
        detailHtml += `</div>
            <div id="content-diff" style="display:none;">
                <p id="diff-loading">Loading diff...</p>
                <div id="diff-viewer"></div>
            </div>
        </div>`;
        
        container.innerHTML = detailHtml;
        
        if (item.mermaid_graph && typeof mermaid !== 'undefined') {
            setTimeout(() => {
                mermaid.run({ querySelector: '.mermaid' }).catch(err => console.log('Mermaid render error', err));
            }, 100);
        }
    };
    
    window.switchTab = async function(tab, pr_number, repo) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
            btn.classList.add('btn-outline');
        });
        document.getElementById(`tab-${tab}`).classList.add('active');
        document.getElementById(`tab-${tab}`).classList.remove('btn-outline');
        
        if (tab === 'summary') {
            document.getElementById('content-summary').style.display = 'block';
            document.getElementById('content-diff').style.display = 'none';
        } else if (tab === 'diff') {
            document.getElementById('content-summary').style.display = 'none';
            document.getElementById('content-diff').style.display = 'block';
            
            const diffViewer = document.getElementById('diff-viewer');
            if (!diffViewer.innerHTML.trim()) {
                try {
                    const res = await apiFetch(`/pr/${pr_number}/diff?repo=${encodeURIComponent(repo)}`);
                    if (res.ok) {
                        const data = await res.json();
                        document.getElementById('diff-loading').style.display = 'none';
                        const diffHtml = Diff2Html.html(data.diff, {
                            drawFileList: true,
                            matching: 'lines',
                            outputFormat: 'side-by-side',
                            colorScheme: localStorage.getItem('theme') || 'dark'
                        });
                        diffViewer.innerHTML = diffHtml;
                    } else {
                        document.getElementById('diff-loading').textContent = "Failed to load diff.";
                    }
                } catch(e) {
                    document.getElementById('diff-loading').textContent = "Error loading diff.";
                }
            }
        }
    };

    window.renderView = renderView;

    async function fetchAnalyses() {
        container.innerHTML = '<p>Loading analyses...</p>';
        try {
            // Fetch global analytics trends for Scorecards
            let trendsHtml = '';
            try {
                const trendsRes = await apiFetch('/analytics/trends?days=7');
                if (trendsRes.ok) {
                    const trendsData = await trendsRes.json();
                    if (trendsData.data && trendsData.data.length > 0) {
                        const latest = trendsData.data[trendsData.data.length - 1];
                        trendsHtml = `
                        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                            <div class="card" style="flex: 1; text-align: center;">
                                <h4>7-Day PRs</h4>
                                <h2 style="font-size: 2rem; color: var(--primary);">${trendsData.data.reduce((a,b) => a + b.total_prs, 0)}</h2>
                            </div>
                            <div class="card" style="flex: 1; text-align: center;">
                                <h4>Avg Quality</h4>
                                <h2 style="font-size: 2rem; color: ${latest.avg_quality_score < 70 ? '#ef4444' : '#22c55e'};">${latest.avg_quality_score}</h2>
                            </div>
                            <div class="card" style="flex: 1; text-align: center;">
                                <h4>Avg Confidence</h4>
                                <h2 style="font-size: 2rem; color: var(--text);">${latest.avg_confidence_score}</h2>
                            </div>
                        </div>`;
                    }
                }
            } catch (e) {
                console.warn("Failed to load trends", e);
            }

            const hRes = await apiFetch(`/analytics/history?limit=50`);
            let allAnalyses = [];
            if (hRes.ok) {
                const hData = await hRes.json();
                allAnalyses = hData.data;
            }
            
            window.currentAnalyses = allAnalyses;
            
            if (allAnalyses.length === 0) {
                container.innerHTML = trendsHtml + '<div class="card"><p>No PR analyses found.</p></div>';
                return;
            }
            
            let html = trendsHtml + '<div class="card"><h3>Recent PR History</h3><div class="table-container"><table><tr><th>PR</th><th>Repo</th><th>Quality</th><th>Confidence</th><th>Author</th></tr>';
            allAnalyses.forEach((item, idx) => {
                let qualityColor = item.quality_score < 70 ? '#ef4444' : (item.quality_score < 90 ? '#f59e0b' : '#22c55e');
                html += `<tr style="cursor: pointer;" onclick="showDetails(${idx})">
                    <td>#${item.pr_number}</td>
                    <td>${item.repo}</td>
                    <td><span class="badge" style="background: rgba(255,255,255,0.1); color: ${qualityColor}">Score: ${item.quality_score}</span></td>
                    <td>${item.confidence_score}</td>
                    <td>${item.author || 'Unknown'}</td>
                </tr>`;
            });
            html += '</table></div>';
            container.innerHTML = html;
        } catch (e) {
            container.innerHTML = `<p class="error">Failed to load analyses</p>`;
        }
    }

    async function fetchSuperAdmin() {
        container.innerHTML = '<p>Loading Super Admin Dashboard...</p>';
        try {
            const res = await apiFetch('/admin/dashboard');
            const data = await res.json();
            
            if (data.status === 'success') {
                const dash = data.data;
                let html = `<div class="card" style="margin-bottom: 20px;">
                    <h3>Teams (Profiles)</h3>
                    <div class="table-container"><table><tr><th>ID</th><th>Name</th><th>Model</th><th>Changelog Repo</th></tr>`;
                
                dash.profiles.forEach(p => {
                    html += `<tr><td>${p.id}</td><td>${p.name}</td><td>${p.ai_model}</td><td>${p.changelog_repo || 'None'}</td></tr>`;
                });
                
                html += `</table></div></div>`;
                
                html += `<div class="card" style="margin-bottom: 20px;">
                    <h3>Active Repositories</h3>
                    <div class="table-container"><table><tr><th>Repository</th><th>Profile ID</th></tr>`;
                
                dash.repository_mappings.forEach(r => {
                    html += `<tr><td>${r.source_repo}</td><td>${r.profile_id}</td></tr>`;
                });
                
                html += `</table></div></div>`;
                
                html += `<div class="card" style="margin-bottom: 20px;">
                    <h3>Recent Global PR Activity</h3>
                    <div class="table-container"><table><tr><th>PR</th><th>Repo</th><th>Status</th><th>Risk</th><th>BRD</th></tr>`;
                
                dash.recent_prs.forEach((item, idx) => {
                    // Make it accessible for details using the existing array if needed, but here just display overview
                    let riskColor = item.risk_level === 'High' ? '#ef4444' : (item.risk_level === 'Medium' ? '#f59e0b' : '#22c55e');
                    html += `<tr>
                        <td>#${item.pr_number}</td>
                        <td>${item.repo}</td>
                        <td><span class="badge" style="background: ${item.approved ? 'rgba(34, 197, 94, 0.2)' : 'rgba(234, 179, 8, 0.2)'}; color: ${item.approved ? '#4ade80' : '#facc15'}">${item.approved ? 'Approved' : 'Pending'}</span></td>
                        <td><span style="color: ${riskColor}; font-weight: bold;">${item.risk_level || 'Low'}</span></td>
                        <td>${item.brd_alignment_score || 0}/100</td>
                    </tr>`;
                });
                
                html += `</table></div></div>`;
                container.innerHTML = html;
            } else {
                container.innerHTML = `<p class="error">Failed to load Super Admin data</p>`;
            }
        } catch (e) {
            container.innerHTML = `<p class="error">Error loading Super Admin Dashboard: ${e.message}</p>`;
        }
    }

    async function fetchSettings() {
        container.innerHTML = '<p>Loading settings...</p>';
        try {
            const profRes = await apiFetch('/profiles/');
            const profiles = await profRes.json();
            
            let defaultProfile = profiles.find(p => p.id === 1) || profiles[0];
            if (!defaultProfile) {
                container.innerHTML = '<p>No profile found.</p>';
                return;
            }

            let html = `
                <div class="card">
                    <h3>Customizable Rule Engine</h3>
                    <p>Define custom rules for PR analysis (e.g., naming conventions, dependency checks, test coverage).</p>
                    <textarea id="custom-rules-input" class="form-input" style="width: 100%; height: 200px; padding: 10px; margin-top: 10px; font-family: monospace; border: 1px solid var(--border); background: rgba(0,0,0,0.1); color: var(--text);">${defaultProfile.custom_rules || ''}</textarea>
                    
                    <h3 style="margin-top: 20px;">BRD Content</h3>
                    <textarea id="brd-content-input" class="form-input" style="width: 100%; height: 200px; padding: 10px; margin-top: 10px; font-family: monospace; border: 1px solid var(--border); background: rgba(0,0,0,0.1); color: var(--text);">${defaultProfile.brd_content || ''}</textarea>
                    
                    <button id="save-settings-btn" class="btn primary-btn" style="margin-top: 15px;">Save Settings</button>
                </div>
            `;
            container.innerHTML = html;

            document.getElementById('save-settings-btn').addEventListener('click', async () => {
                const rules = document.getElementById('custom-rules-input').value;
                const brd = document.getElementById('brd-content-input').value;
                
                const btn = document.getElementById('save-settings-btn');
                btn.textContent = 'Saving...';
                btn.disabled = true;

                try {
                    const updatePayload = {
                        name: defaultProfile.name,
                        changelog_repo: defaultProfile.changelog_repo,
                        ai_model: defaultProfile.ai_model,
                        github_token: defaultProfile.github_token,
                        brd_content: brd,
                        custom_rules: rules
                    };
                    const res = await apiFetch('/profiles/' + defaultProfile.id, {
                        method: 'PUT',
                        body: JSON.stringify(updatePayload)
                    });
                    
                    if (res.ok) {
                        alert("Settings saved successfully!");
                    } else {
                        const err = await res.json();
                        alert("Error saving settings: " + (err.detail || "Unknown error"));
                    }
                } catch(e) {
                    alert("Failed to save settings: " + e.message);
                } finally {
                    btn.textContent = 'Save Settings';
                    btn.disabled = false;
                }
            });

        } catch (e) {
            container.innerHTML = `<p class="error">Failed to load settings: ${e.message}</p>`;
        }
    }

    // Init
    renderView('home');
});
