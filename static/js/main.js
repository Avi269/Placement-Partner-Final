/*
============================================================================
PLACEMENT PARTNER - Main JavaScript File
============================================================================
This file handles client-side interactions for the placement partner app:
- File upload with drag-and-drop
- Form validation
- AJAX submissions
- Dynamic UI updates
- Progress indicators
- Tooltips and animations
============================================================================
*/

// Initialize all components when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all interactive components
    initFileUpload();        // File upload with drag & drop
    initFormValidation();    // Client-side form validation
    initTooltips();          // Bootstrap tooltips
    initAnimations();        // Page animations
    initProgressBars();      // Animated progress bars
});

// ============================================================================
// FILE UPLOAD HANDLING
// ============================================================================
// Handles file uploads with drag-and-drop functionality and visual feedback

function initFileUpload() {
    /**
     * Initialize drag-and-drop file upload areas
     * 
     * Features:
     * - Drag and drop files
     * - Click to browse
     * - File validation
     * - Visual feedback
     * - Display selected files
     */
    // Find all file upload areas on the page
    const fileUploadAreas = document.querySelectorAll('.file-upload-area');
    
    fileUploadAreas.forEach(area => {
        // Get child elements
        const input = area.querySelector('input[type="file"]');
        const dropText = area.querySelector('.drop-text');
        const fileList = area.querySelector('.file-list');
        
        // Skip if no file input found
        if (!input) return;
        
        // === DRAG AND DROP EVENTS ===
        
        // When file is dragged over the area
        area.addEventListener('dragover', (e) => {
            e.preventDefault();  // Prevent default browser behavior
            area.classList.add('dragover');  // Add visual feedback
        });
        
        // When file leaves the drag area
        area.addEventListener('dragleave', () => {
            area.classList.remove('dragover');  // Remove visual feedback
        });
        
        // When file is dropped
        area.addEventListener('drop', (e) => {
            e.preventDefault();  // Prevent file from opening in browser
            area.classList.remove('dragover');
            const files = e.dataTransfer.files;  // Get dropped files
            handleFiles(files, input, fileList);  // Process files
        });
        
        // === TRADITIONAL FILE INPUT ===
        
        // When user selects files via browse dialog
        input.addEventListener('change', (e) => {
            handleFiles(e.target.files, input, fileList);
        });
        
        // Make entire area clickable to trigger file browser
        area.addEventListener('click', () => {
            input.click();  // Programmatically open file dialog
        });
    });
}

function handleFiles(files, input, fileList) {
    /**
     * Process selected or dropped files
     * 
     * @param {FileList} files - Files to process
     * @param {HTMLElement} input - File input element
     * @param {HTMLElement} fileList - Container to display file list
     * 
     * Actions:
     * 1. Update file input with selected files
     * 2. Display file names and sizes
     * 3. Auto-submit form if enabled
     */
    if (files.length === 0) return;
    
    // Update the file input element with selected files
    input.files = files;
    
    // Display list of selected files with icons and sizes
    if (fileList) {
        fileList.innerHTML = '';  // Clear existing list
        
        // Create a UI element for each file
        Array.from(files).forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item d-flex align-items-center p-2 border rounded mb-2';
            fileItem.innerHTML = `
                <i class="fas fa-file me-2 text-primary"></i>
                <span class="flex-grow-1">${file.name}</span>
                <small class="text-muted">${formatFileSize(file.size)}</small>
            `;
            fileList.appendChild(fileItem);
        });
    }
    
    // Auto-submit form if data-auto-submit="true" attribute is set
    const form = input.closest('form');
    if (form && form.dataset.autoSubmit === 'true') {
        submitForm(form);
    }
}

function formatFileSize(bytes) {
    /**
     * Convert bytes to human-readable file size
     * 
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted size (e.g., "2.5 MB")
     */
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;  // 1 KB = 1024 bytes
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    
    // Calculate appropriate unit (KB, MB, etc.)
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    // Format to 2 decimal places
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ============================================================================
// FORM VALIDATION AND SUBMISSION
// ============================================================================
// Client-side form validation before submitting to server

function initFormValidation() {
    /**
     * Initialize client-side form validation
     * 
     * Validates forms marked with data-validate="true"
     * Checks required fields before submission
     */
    const forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(form => {
        // Intercept form submission for validation
        form.addEventListener('submit', (e) => {
            if (!validateForm(form)) {
                e.preventDefault();  // Stop submission if validation fails
                return false;
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            showFieldError(input, 'This field is required');
            isValid = false;
        } else {
            clearFieldError(input);
        }
    });
    
    // Email validation
    const emailInputs = form.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        if (input.value && !isValidEmail(input.value)) {
            showFieldError(input, 'Please enter a valid email address');
            isValid = false;
        }
    });
    
    return isValid;
}

function showFieldError(input, message) {
    clearFieldError(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback d-block';
    errorDiv.textContent = message;
    
    input.classList.add('is-invalid');
    input.parentNode.appendChild(errorDiv);
}

function clearFieldError(input) {
    input.classList.remove('is-invalid');
    const errorDiv = input.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Form Submission with AJAX
function submitForm(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.innerHTML : '';
    
    // Show loading state
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>Processing...';
    }
    
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: form.method || 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message || 'Operation completed successfully!');
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }
        } else {
            showAlert('danger', data.message || 'An error occurred. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', 'An error occurred. Please try again.');
    })
    .finally(() => {
        // Restore button state
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

// Alert System
function showAlert(type, message, duration = 5000) {
    const alertContainer = document.getElementById('alert-container') || createAlertContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after duration
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, duration);
}

function createAlertContainer() {
    const container = document.createElement('div');
    container.id = 'alert-container';
    container.className = 'position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// Tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Animations
function initAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

// Progress Bars
function initProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar[data-progress]');
    
    progressBars.forEach(bar => {
        const progress = bar.dataset.progress;
        animateProgressBar(bar, progress);
    });
}

function animateProgressBar(bar, targetProgress) {
    let currentProgress = 0;
    const increment = targetProgress / 50; // 50 steps for smooth animation
    
    const interval = setInterval(() => {
        currentProgress += increment;
        if (currentProgress >= targetProgress) {
            currentProgress = targetProgress;
            clearInterval(interval);
        }
        
        bar.style.width = currentProgress + '%';
        bar.textContent = Math.round(currentProgress) + '%';
    }, 20);
}

// Job Matching Visualization
function updateJobFitScore(score) {
    const fitScoreElement = document.getElementById('job-fit-score');
    if (!fitScoreElement) return;
    
    fitScoreElement.textContent = score + '%';
    
    // Update color based on score
    fitScoreElement.className = 'fit-score';
    if (score >= 80) {
        fitScoreElement.classList.add('high');
    } else if (score >= 60) {
        fitScoreElement.classList.add('medium');
    } else {
        fitScoreElement.classList.add('low');
    }
}

// Skill Tags Management
function createSkillTags(skills, container, type = 'default') {
    if (!container) return;
    
    container.innerHTML = '';
    skills.forEach(skill => {
        const tag = document.createElement('span');
        tag.className = `skill-tag ${type}`;
        tag.textContent = skill;
        container.appendChild(tag);
    });
}

// Cover Letter Preview
function updateCoverLetterPreview(text) {
    const previewElement = document.getElementById('cover-letter-preview');
    if (!previewElement) return;
    
    previewElement.innerHTML = text.replace(/\n/g, '<br>');
    previewElement.scrollTop = 0;
}

// Offer Analysis Display
function displayOfferAnalysis(analysis) {
    const container = document.getElementById('offer-analysis-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="offer-analysis">
            <h4 class="mb-3">Analysis Results</h4>
            
            <div class="row">
                <div class="col-md-6">
                    <h5>Key Information</h5>
                    <ul class="list-unstyled">
                        <li><strong>CTC:</strong> ${analysis.ctc || 'Not specified'}</li>
                        <li><strong>Probation Period:</strong> ${analysis.probation_period || 'Not specified'}</li>
                        <li><strong>Notice Period:</strong> ${analysis.notice_period || 'Not specified'}</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h5>Risk Assessment</h5>
                    <div id="risk-flags">
                        ${analysis.risk_flags ? analysis.risk_flags.map(flag => 
                            `<div class="risk-flag"><i class="fas fa-exclamation-triangle me-2"></i>${flag}</div>`
                        ).join('') : '<p class="text-muted">No significant risks identified</p>'}
                    </div>
                </div>
            </div>
            
            <div class="mt-4">
                <h5>Summary</h5>
                <p>${analysis.explanation || 'Analysis completed successfully.'}</p>
            </div>
        </div>
    `;
}

// Dashboard Charts (if Chart.js is available)
function initDashboardCharts() {
    if (typeof Chart === 'undefined') return;
    
    // Applications Chart
    const applicationsCtx = document.getElementById('applications-chart');
    if (applicationsCtx) {
        new Chart(applicationsCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Applications',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        });
    }
    
    // Skills Chart
    const skillsCtx = document.getElementById('skills-chart');
    if (skillsCtx) {
        new Chart(skillsCtx, {
            type: 'doughnut',
            data: {
                labels: ['Python', 'JavaScript', 'React', 'Django', 'SQL'],
                datasets: [{
                    data: [30, 25, 20, 15, 10],
                    backgroundColor: [
                        '#2563eb',
                        '#10b981',
                        '#f59e0b',
                        '#ef4444',
                        '#8b5cf6'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    }
                }
            }
        });
    }
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Export functions for global use
window.PlacementPartner = {
    showAlert,
    updateJobFitScore,
    createSkillTags,
    updateCoverLetterPreview,
    displayOfferAnalysis,
    submitForm,
    debounce,
    throttle
}; 