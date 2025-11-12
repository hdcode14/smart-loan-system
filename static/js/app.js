// Tab functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tabs
    initializeTabs();
    
    // Initialize EMI repayment functionality
    initializeEMIRepayment();
    
    // Initialize wallet functionality
    initializeWallet();
    
    // Initialize admin functionality
    initializeAdmin();
    
    // Initialize charts if on dashboard
    if (document.getElementById('dashboard')) {
        initializeCharts();
    }
});

function initializeTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab
            tab.classList.add('active');
            
            // Show corresponding content
            const tabId = tab.getAttribute('data-tab');
            const content = document.getElementById(`${tabId}-tab`);
            if (content) {
                content.classList.add('active');
            }
        });
    });
}

function initializeEMIRepayment() {
    // EMI repayment - with loan status validation
    const repayButtons = document.querySelectorAll('.repay-emi');
    repayButtons.forEach(button => {
        button.addEventListener('click', function() {
            const repaymentId = this.getAttribute('data-repayment-id');
            const amount = this.getAttribute('data-amount');
            const emiAmount = this.getAttribute('data-emi-amount');
            const penalty = this.getAttribute('data-penalty');
            
            // Check if wallet has sufficient balance
            const walletBalance = parseFloat(document.querySelector('.stat-card .stat-value')?.textContent?.replace('₹', '') || '0');
            const totalAmount = parseFloat(amount);
            
            if (walletBalance < totalAmount) {
                let message = `Insufficient wallet balance. You have ₹${walletBalance.toFixed(2)} but need ₹${totalAmount.toFixed(2)}`;
                if (penalty > 0) {
                    message += ` (EMI: ₹${emiAmount} + Penalty: ₹${penalty})`;
                }
                alert(message);
                return;
            }
            
            let confirmMessage = `Are you sure you want to pay ₹${totalAmount.toFixed(2)} for this EMI?`;
            if (penalty > 0) {
                confirmMessage += `\n\nThis includes ₹${penalty} late penalty.`;
            }
            
            if (confirm(confirmMessage)) {
                fetch(`/api/repay-emi/${repaymentId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error processing payment');
                });
            }
        });
    });
}

function initializeWallet() {
    // Wallet functionality is now handled by addWalletFunds()
}

function initializeAdmin() {
    // Admin loan approval
    const approveButtons = document.querySelectorAll('.approve-loan');
    approveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const loanId = this.getAttribute('data-loan-id');
            const borrowerName = this.getAttribute('data-borrower-name');
            
            if (confirm(`Approve loan application for ${borrowerName}?`)) {
                fetch(`/api/approve-loan/${loanId}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error approving loan');
                });
            }
        });
    });
    
    // Admin loan disbursement
    const disburseButtons = document.querySelectorAll('.disburse-loan');
    disburseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const loanId = this.getAttribute('data-loan-id');
            const borrowerName = this.getAttribute('data-borrower-name');
            
            if (confirm(`Disburse loan amount to ${borrowerName}'s wallet?`)) {
                fetch(`/api/disburse-loan/${loanId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ method: 'wallet' })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error disbursing loan');
                });
            }
        });
    });
    
    // Admin loan rejection
    const rejectButtons = document.querySelectorAll('.reject-loan');
    rejectButtons.forEach(button => {
        button.addEventListener('click', function() {
            const loanId = this.getAttribute('data-loan-id');
            const borrowerName = this.getAttribute('data-borrower-name');
            
            if (confirm(`Reject loan application for ${borrowerName}?`)) {
                fetch(`/api/reject-loan/${loanId}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        location.reload();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error rejecting loan');
                });
            }
        });
    });
}

function signAgreement(loanId) {
    if (confirm('By signing this agreement, you agree to all terms and conditions. This action is legally binding and cannot be undone. Do you want to proceed?')) {
        fetch(`/api/sign-agreement/${loanId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(' Agreement signed successfully! Your loan will now be processed for disbursement.');
                location.reload();
            } else {
                alert(' Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert(' Error signing agreement. Please try again.');
        });
    }
}

function addWalletFunds() {
    const amountInput = prompt('Enter amount to add to wallet:');
    const amount = parseFloat(amountInput);
    
    if (amount && amount > 0) {
        fetch('/api/add-wallet-funds', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                amount: amount
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error adding funds');
        });
    } else if (amountInput !== null) {
        alert('Please enter a valid amount greater than 0');
    }
}

function showLoanDetails(loanId) {
    // Redirect to loan details page
    window.location.href = `/loan-details/${loanId}`;
}

function initializeCharts() {
    // Financial Health Chart
    const healthCtx = document.getElementById('financialHealthChart');
    if (healthCtx) {
        // Simple health indicator
        const healthScore = parseInt(document.getElementById('healthScore')?.getAttribute('data-score') || '650');
        const healthColor = healthScore >= 700 ? '#10b981' : healthScore >= 600 ? '#f59e0b' : '#ef4444';
        
        // Create a simple progress circle
        const ctx = healthCtx.getContext('2d');
        const centerX = healthCtx.width / 2;
        const centerY = healthCtx.height / 2;
        const radius = 40;
        
        // Background circle
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 8;
        ctx.stroke();
        
        // Progress circle
        const progress = (healthScore - 300) / 550; // Convert 300-850 to 0-1
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, -0.5 * Math.PI, (2 * progress - 0.5) * Math.PI);
        ctx.strokeStyle = healthColor;
        ctx.lineWidth = 8;
        ctx.stroke();
        
        // Score text
        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 20px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(healthScore, centerX, centerY);
        
        // Label
        ctx.font = '12px Arial';
        ctx.fillText('Score', centerX, centerY + 25);
    }
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Auto-format currency inputs
document.addEventListener('DOMContentLoaded', function() {
    const currencyInputs = document.querySelectorAll('input[type="number"]');
    currencyInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value) {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });
});

// Enhanced error handling for API calls
function handleApiError(error) {
    console.error('API Error:', error);
    if (error.status === 401) {
        alert('Session expired. Please login again.');
        window.location.href = '/login';
    } else if (error.status === 403) {
        alert('Access denied. You do not have permission for this action.');
    } else {
        alert('An error occurred. Please try again.');
    }
}

// Add CSRF protection for forms
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// Enhanced fetch with error handling
async function apiFetch(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': getCSRFToken()
        },
        credentials: 'same-origin'
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, mergedOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Loan application form validation
function validateLoanForm(formData) {
    const errors = [];
    
    if (!formData.amount || formData.amount < 1000) {
        errors.push('Loan amount must be at least ₹1,000');
    }
    
    if (!formData.purpose) {
        errors.push('Please select a loan purpose');
    }
    
    if (!formData.duration || formData.duration < 6) {
        errors.push('Loan duration must be at least 6 months');
    }
    
    return errors;
}

// Real-time form validation
document.addEventListener('DOMContentLoaded', function() {
    const loanForm = document.getElementById('loanForm');
    if (loanForm) {
        loanForm.addEventListener('submit', function(e) {
            const formData = new FormData(this);
            const amount = parseFloat(formData.get('amount'));
            const purpose = formData.get('purpose');
            const duration = parseInt(formData.get('duration'));
            
            const errors = validateLoanForm({ amount, purpose, duration });
            
            if (errors.length > 0) {
                e.preventDefault();
                alert('Please fix the following errors:\n\n' + errors.join('\n'));
            }
        });
    }
});

// Auto-refresh dashboard data
function startDashboardAutoRefresh() {
    if (window.location.pathname === '/dashboard' || window.location.pathname === '/admin/dashboard') {
        setInterval(() => {
            // Refresh page every 2 minutes
            window.location.reload();
        }, 120000); // 2 minutes
    }
}

// Initialize auto-refresh
document.addEventListener('DOMContentLoaded', startDashboardAutoRefresh);

// Enhanced number formatting for Indian currency
function formatIndianCurrency(amount) {
    if (isNaN(amount)) return '₹0.00';
    
    const formatter = new Intl.NumberFormat('en-IN', {
        maximumFractionDigits: 2,
        minimumFractionDigits: 2
    });
    
    return '₹' + formatter.format(amount);
}

// Update all currency displays on page load
document.addEventListener('DOMContentLoaded', function() {
    const currencyElements = document.querySelectorAll('[data-currency]');
    currencyElements.forEach(element => {
        const amount = parseFloat(element.getAttribute('data-currency'));
        if (!isNaN(amount)) {
            element.textContent = formatIndianCurrency(amount);
        }
    });
});