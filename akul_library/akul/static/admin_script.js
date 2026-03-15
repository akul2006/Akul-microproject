// Initialize on load
function checkHash() {
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');
    const openIssue = urlParams.get('open_issue');
    
    if (tab && document.getElementById(tab)) {
        showPage(tab);
        
        // Auto-open Issue Modal if triggered by QR Code
        if (tab === 'circulations' && openIssue === 'true') {
            const isbn = urlParams.get('isbn');
            openIssueBookModal();
            
            // Auto-fill Book
            const bookSelect = document.querySelector('#issueBookModal select[name="book"]');
            if(bookSelect && isbn) {
                const cleanIsbn = isbn.replace(/[^0-9X]/gi, '');
                const option = Array.from(bookSelect.options).find(opt => {
                    const optIsbn = opt.getAttribute('data-isbn') || '';
                    return optIsbn.replace(/[^0-9X]/gi, '') === cleanIsbn;
                });
                if (option) bookSelect.value = option.value;
            }
            
            // Auto-fill Date (Today)
            const dateInput = document.querySelector('#issueBookModal input[name="issue_date"]');
            if(dateInput) {
                dateInput.value = new Date().toISOString().split('T')[0];
            }
        }
    } else if (window.location.hash) {
        const pageName = window.location.hash.substring(1);
        if (document.getElementById(pageName)) showPage(pageName);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const allTimeCheckbox = document.getElementById('allTimeCheckbox');
    if (allTimeCheckbox) toggleDateInputs(allTimeCheckbox);
});

document.addEventListener('DOMContentLoaded', checkHash);
// Check immediately in case the script runs after DOMContentLoaded
checkHash();

window.addEventListener('popstate', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab') || 'dashboard';
    if (document.getElementById(tab)) {
        showPage(tab);
    }
});

// Page Navigation
function showPage(pageName) {
    // Hide all pages
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => page.classList.remove('active'));

    // Remove active class from all nav links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => link.classList.remove('active'));

    // Show selected page
    document.getElementById(pageName).classList.add('active');

    // Add active class to corresponding nav link
    navLinks.forEach(link => {
        const onclick = link.getAttribute('onclick');
        if (onclick && onclick.includes("'" + pageName + "'")) {
            link.classList.add('active');
        }
    });

    // Update URL to keep track of current tab
    const url = new URL(window.location);
    if (url.searchParams.get('tab') !== pageName) {
        url.searchParams.set('tab', pageName);
        url.searchParams.delete('open_issue');
        window.history.pushState({}, '', url);
    }
}

// Notification Logic
function toggleNotifications(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('notificationDropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

function toggleProfileDropdown(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('profileDropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

window.addEventListener('click', function (event) {
    const dropdown = document.getElementById('notificationDropdown');
    if (dropdown && dropdown.classList.contains('active') && !dropdown.contains(event.target)) {
        dropdown.classList.remove('active');
    }

    const profileDropdown = document.getElementById('profileDropdown');
    if (profileDropdown && profileDropdown.classList.contains('active') && !profileDropdown.contains(event.target)) {
        profileDropdown.classList.remove('active');
    }
});

function openPublisherModal(card) {
    const modal = document.getElementById('publisherBooksModal');
    const name = card.getAttribute('data-name');
    const booksHtml = card.querySelector('.publisher-books-data').innerHTML;

    document.getElementById('modalPublisherName').innerText = name;
    document.getElementById('modalBooksList').innerHTML = booksHtml;
    modal.style.display = "block";
}

function closePublisherModal() {
    document.getElementById('publisherBooksModal').style.display = "none";
}

// Author Modal Functions
function openAddAuthorModal() {
    document.getElementById('addAuthorModal').style.display = "block";
}

function closeAddAuthorModal() {
    document.getElementById('addAuthorModal').style.display = "none";
}

function openEditAuthorModal(id, name, bio) {
    document.getElementById('editAuthorId').value = id;
    document.getElementById('editAuthorName').value = name;
    document.getElementById('editAuthorBio').value = bio;
    document.getElementById('editAuthorModal').style.display = "block";
}

function closeEditAuthorModal() {
    document.getElementById('editAuthorModal').style.display = "none";
}

function deleteAuthor(id) {
    if (confirm("Are you sure you want to delete this author?")) {
        window.location.href = "/delete_author/" + id;
    }
}

function openAuthorBooksModal(btn) {
    const modal = document.getElementById('authorBooksModal');
    const row = btn.closest('tr');
    const name = row.querySelector('.author-name-text').innerText;
    const booksHtml = row.querySelector('.author-books-data').innerHTML;

    document.getElementById('modalAuthorBooksName').innerText = name + "'s Books";
    document.getElementById('modalAuthorBooksList').innerHTML = booksHtml;
    modal.style.display = "block";
}

function closeAuthorBooksModal() {
    document.getElementById('authorBooksModal').style.display = "none";
}

// Book Modal Functions
function openAddBookModal() {
    document.getElementById('addBookModal').style.display = "block";
}

function closeAddBookModal() {
    document.getElementById('addBookModal').style.display = "none";
}

async function fetchBookDetails() {
    const isbnInput = document.getElementById('addBookIsbnInput');
    const feedback = document.getElementById('isbnFeedback');
    
    if (!isbnInput || !isbnInput.value.trim()) {
        feedback.style.color = '#dc3545';
        feedback.innerText = 'Please enter an ISBN first.';
        return;
    }

    // Remove non-numeric characters (allow 'X' for ISBN-10)
    const isbn = isbnInput.value.trim().replace(/[^0-9X]/gi, '');
    feedback.style.color = '#007bff';
    feedback.innerText = 'Fetching details from Google Books...';

    try {
        const response = await fetch(`https://www.googleapis.com/books/v1/volumes?q=isbn:${isbn}`);
        const data = await response.json();

        if (data.totalItems > 0 && data.items && data.items.length > 0) {
            const book = data.items[0].volumeInfo;

                fillBookForm(
                    book.title,
                    book.authors ? book.authors[0] : '',
                    book.publisher || '',
                    (book.imageLinks && book.imageLinks.thumbnail) ? book.imageLinks.thumbnail.replace(/^http:\/\//i, 'https://') : ''
                );

            feedback.style.color = '#28a745';
                feedback.innerText = 'Book details fetched successfully from Google Books!';
                return;
            }

            // Fallback: Open Library API
            feedback.innerText = 'Not found in Google. Trying Open Library...';
            const olResponse = await fetch(`https://openlibrary.org/api/books?bibkeys=ISBN:${isbn}&format=json&jscmd=data`);
            const olData = await olResponse.json();
            const olKey = `ISBN:${isbn}`;

            if (olData[olKey]) {
                const book = olData[olKey];
                fillBookForm(
                    book.title,
                    (book.authors && book.authors.length > 0) ? book.authors[0].name : '',
                    (book.publishers && book.publishers.length > 0) ? book.publishers[0].name : '',
                    (book.cover && book.cover.medium) ? book.cover.medium : ''
                );

                feedback.style.color = '#28a745';
                feedback.innerText = 'Book details fetched successfully from Open Library!';
        } else {
            feedback.style.color = '#dc3545';
                feedback.innerText = 'Book not found in Google Books or Open Library.';
        }
    } catch (error) {
        console.error('Error fetching book details:', error);
        feedback.style.color = '#dc3545';
        feedback.innerText = 'Error fetching details. Please try again.';
    }
}

function fillBookForm(title, author, publisher, imageUrl) {
    if (title) document.getElementById('addBookTitle').value = title;

    if (author) {
        const authorSelect = document.querySelector('#addBookModal select[name="author"]');
        if (authorSelect) authorSelect.value = ""; 
        document.getElementById('addBookNewAuthor').value = author;
    }

    if (publisher) {
        const publisherSelect = document.querySelector('#addBookModal select[name="publisher"]');
        if (publisherSelect) publisherSelect.value = ""; 
        document.getElementById('addBookNewPublisher').value = publisher;
    }

    if (imageUrl) {
        document.getElementById('addBookImageUrl').value = imageUrl;
    }
}

function openEditBookModal(id, title, authorId, isbn, totalQty, availQty, imageUrl, location) {
    document.getElementById('editBookId').value = id;
    document.getElementById('editBookTitle').value = title;
    document.getElementById('editBookAuthor').value = authorId;
    document.getElementById('editBookIsbn').value = isbn;
    document.getElementById('editBookTotalQty').value = totalQty;
    document.getElementById('editBookAvailQty').value = availQty;
    document.getElementById('editBookImage').value = imageUrl;

    if (document.getElementById('editBookLocation')) document.getElementById('editBookLocation').value = location || '';
    document.getElementById('editBookModal').style.display = "block";
}

function closeEditBookModal() {
    document.getElementById('editBookModal').style.display = "none";
}

function deleteBook(id) {
    if (confirm("Are you sure you want to delete this book?")) {
        window.location.href = "/delete_book/" + id + "/";
    }
}

function openAddPublisherModal() {
    document.getElementById('addPublisherModal').style.display = "block";
}

function closeAddPublisherModal() {
    document.getElementById('addPublisherModal').style.display = "none";
}

function openEditPublisherModal(id, name) {
    document.getElementById('editPublisherId').value = id;
    document.getElementById('editPublisherName').value = name;
    document.getElementById('editPublisherModal').style.display = "block";
}

function closeEditPublisherModal() {
    document.getElementById('editPublisherModal').style.display = "none";
}

// User Modal Functions
function openAddUserModal() {
    document.getElementById('addUserModal').style.display = "block";
}

function closeAddUserModal() {
    document.getElementById('addUserModal').style.display = "none";
}

// Edit User Modal Functions
function openEditUserModal(id, username, email, isSuperuser, isActive) {
    document.getElementById('editUserId').value = id;
    document.getElementById('editUserUsername').value = username;
    document.getElementById('editUserEmail').value = email;
    
    // Convert Python boolean strings to JS booleans/strings
    const isAdmin = (isSuperuser === 'True' || isSuperuser === 'true');
    const isActiveBool = (isActive === 'True' || isActive === 'true');

    document.getElementById('editUserRole').value = isAdmin ? 'True' : 'False';
    document.getElementById('editUserStatus').value = isActiveBool ? 'True' : 'False';
    
    document.getElementById('editUserModal').style.display = "block";
}

function closeEditUserModal() {
    document.getElementById('editUserModal').style.display = "none";
}

// Penalty Modal Functions
function openAddPenaltyModal() {
    document.getElementById('addPenaltyModal').style.display = "block";
}

function closeAddPenaltyModal() {
    document.getElementById('addPenaltyModal').style.display = "none";
}

// Issue Book Modal Functions
function openIssueBookModal() {
    const modal = document.getElementById('issueBookModal');
    if (modal) {
        modal.style.display = "block";
    } else {
        console.error("Issue Book Modal not found");
    }
}

function closeIssueBookModal() {
    document.getElementById('issueBookModal').style.display = "none";
}

// Member Modal Functions
function openAddMemberModal() {
    document.getElementById('addMemberModal').style.display = "block";
}

function closeAddMemberModal() {
    document.getElementById('addMemberModal').style.display = "none";
}

function openEditMemberModal(id, name, email, phone, address) {
    document.getElementById('editMemberId').value = id;
    document.getElementById('editMemberName').value = name;
    document.getElementById('editMemberEmail').value = email;
    document.getElementById('editMemberPhone').value = phone;
    document.getElementById('editMemberAddress').value = address;
    document.getElementById('editMemberModal').style.display = "block";
}

function closeEditMemberModal() {
    document.getElementById('editMemberModal').style.display = "none";
}

function openEmailStudentModal(email) {
    const studentSelect = document.getElementById('emailStudentAddress');
    const customEmailInput = document.getElementById('customEmailAddress');
    
    if(studentSelect) {
        studentSelect.value = '';
        if(customEmailInput) {
            customEmailInput.value = '';
            customEmailInput.style.display = 'none';
        }
        document.getElementById('emailTemplateSelector').value = 'custom';
        document.getElementById('emailSubject').value = '';
        document.getElementById('emailMessage').value = '';
        if(document.getElementById('overdueBooksArea')) document.getElementById('overdueBooksArea').style.display = 'none';

        if (email) {
            let optionExists = false;
            for (let i = 0; i < studentSelect.options.length; i++) {
                if (studentSelect.options[i].value === email) {
                    studentSelect.value = email;
                    optionExists = true;
                    break;
                }
            }
            if (!optionExists && customEmailInput) {
                studentSelect.value = 'custom';
                customEmailInput.value = email;
                customEmailInput.style.display = 'block';
            }
        }
        
        if (typeof updateStudentEmailContext === 'function') {
            updateStudentEmailContext();
        }
    }
    
    document.getElementById('emailStudentModal').style.display = "block";
}

function updateStudentEmailContext() {
    const studentSelect = document.getElementById('emailStudentAddress');
    const customEmailInput = document.getElementById('customEmailAddress');
    const overdueArea = document.getElementById('overdueBooksArea');
    const overdueList = document.getElementById('overdueBooksList');
    
    if(!studentSelect) return;

    if (studentSelect.value === 'custom') {
        if(customEmailInput) {
            customEmailInput.style.display = 'block';
            customEmailInput.required = true;
        }
        if(overdueArea) overdueArea.style.display = 'none';
    } else {
        if(customEmailInput) {
            customEmailInput.style.display = 'none';
            customEmailInput.required = false;
        }
        
        const email = studentSelect.value;
        if (typeof overdueData !== 'undefined' && email && overdueData[email] && overdueData[email].length > 0) {
            if(overdueArea) overdueArea.style.display = 'block';
            if(overdueList) {
                overdueList.innerHTML = '';
                overdueData[email].forEach(function(book) {
                    let li = document.createElement('li');
                    li.innerText = book;
                    overdueList.appendChild(li);
                });
            }
        } else {
            if(overdueArea) overdueArea.style.display = 'none';
        }
    }
    
    const template = document.getElementById('emailTemplateSelector');
    if (template && template.value !== 'custom') {
        applyEmailTemplate();
    }
}

function applyEmailTemplate() {
    const template = document.getElementById('emailTemplateSelector').value;
    const subject = document.getElementById('emailSubject');
    const message = document.getElementById('emailMessage');
    
    const studentSelect = document.getElementById('emailStudentAddress');
    let studentName = "Student";
    let email = studentSelect ? studentSelect.value : '';
    
    if (studentSelect && studentSelect.selectedIndex > 0 && studentSelect.value !== 'custom') {
        studentName = studentSelect.options[studentSelect.selectedIndex].getAttribute('data-name');
    }
    
    let adminName = typeof currentAdminName !== 'undefined' ? currentAdminName : 'Admin';
    let libraryName = typeof currentLibraryName !== 'undefined' ? currentLibraryName : 'Library';
    
    let booksText = "";
    if (typeof overdueData !== 'undefined' && email && overdueData[email] && overdueData[email].length > 0) {
        booksText = "\n\nOverdue Books:\n- " + overdueData[email].join('\n- ');
    }

    if (template === 'welcome') {
        subject.value = `Welcome to ${libraryName}!`;
        message.value = `Dear ${studentName},\n\nWelcome to ${libraryName}! Your account has been successfully created. You can now visit the library and start borrowing books from our vast collection.\n\nPlease let us know if you have any questions.\n\nRegards,\n${adminName}`;
    } else if (template === 'overdue') {
        subject.value = 'URGENT: Overdue Book Notice';
        message.value = `Dear ${studentName},\n\nThis is an important notice regarding one or more books on your account that are currently overdue.${booksText}\n\nPlease return them as soon as possible to avoid any further penalties.\n\nRegards,\n${adminName}`;
    } else if (template === 'reminder') {
        subject.value = 'Reminder: Book Due Soon';
        message.value = `Dear ${studentName},\n\nThis is a friendly reminder that a book you borrowed is due very soon. Please ensure you return it on or before the due date to avoid late fees.\n\nRegards,\n${adminName}`;
    }
}

function closeEmailStudentModal() {
    document.getElementById('emailStudentModal').style.display = "none";
}

function openGenerateReportModal() {
    document.getElementById('generateReportModal').style.display = "block";
}

function closeGenerateReportModal() {
    document.getElementById('generateReportModal').style.display = "none";
    document.querySelector('#generateReportModal input[name="start_date"]').value = '';
    document.querySelector('#generateReportModal input[name="end_date"]').value = '';
    const allTimeCheckbox = document.getElementById('allTimeCheckbox');
    if (allTimeCheckbox) {
        allTimeCheckbox.checked = false;
        toggleDateInputs(allTimeCheckbox);
    }
}


let html5QrcodeScanner;

function openScanBarcodeModal() {
    document.getElementById('scanQRModal').style.display = 'block';
    
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear().catch(error => {
            console.error("Failed to clear existing scanner", error);
        }).finally(() => {
            startScanner();
        });
    } else {
        startScanner();
    }
}

function startScanner() {
    const config = { 
        fps: 10,
        useBarCodeDetectorIfSupported: true // Uses OS native barcode scanning if available
    };
    html5QrcodeScanner = new Html5QrcodeScanner("qr-reader", config);
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}

function onScanSuccess(decodedText, decodedResult) {
    html5QrcodeScanner.clear().then(() => {
        const url = new URL(window.location.href);
        url.searchParams.set('tab', 'circulations');
        url.searchParams.set('open_issue', 'true');
        url.searchParams.set('isbn', decodedText);
        window.location.href = url.toString();
    }).catch(err => {
        console.error(err);
    });
}

function onScanFailure(error) {
    // Suppress console errors when a frame/image doesn't immediately yield a barcode
}

function closeScanQRModal() {
    document.getElementById('scanQRModal').style.display = 'none';
    if(html5QrcodeScanner) {
        html5QrcodeScanner.clear().then(() => {
            html5QrcodeScanner = null;
        }).catch(error => {
            console.error("Failed to clear scanner", error);
            html5QrcodeScanner = null;
        });
    }
}

window.onclick = function (event) {
    const modal = document.getElementById('publisherBooksModal');
    const addAuthorModal = document.getElementById('addAuthorModal');
    const editAuthorModal = document.getElementById('editAuthorModal');
    const authorBioModal = document.getElementById('authorBioModal');
    const authorBooksModal = document.getElementById('authorBooksModal');
    const addBookModal = document.getElementById('addBookModal');
    const editBookModal = document.getElementById('editBookModal');
    const addPublisherModal = document.getElementById('addPublisherModal');
    const editPublisherModal = document.getElementById('editPublisherModal');
    const addUserModal = document.getElementById('addUserModal');
    const editUserModal = document.getElementById('editUserModal');
    const addPenaltyModal = document.getElementById('addPenaltyModal');
    const addMemberModal = document.getElementById('addMemberModal');
    const editMemberModal = document.getElementById('editMemberModal');
    const issueBookModal = document.getElementById('issueBookModal');
    const emailStudentModal = document.getElementById('emailStudentModal');
    const viewQRModal = document.getElementById('viewQRModal');
    const scanQRModal = document.getElementById('scanQRModal');
    const generateReportModal = document.getElementById('generateReportModal');

    if (event.target == modal) {
        modal.style.display = "none";
    } else if (event.target == addAuthorModal) {
        addAuthorModal.style.display = "none";
    } else if (event.target == editAuthorModal) {
        editAuthorModal.style.display = "none";
    } else if (authorBioModal && event.target == authorBioModal) {
        authorBioModal.style.display = "none";
    } else if (authorBooksModal && event.target == authorBooksModal) {
        authorBooksModal.style.display = "none";
    } else if (addBookModal && event.target == addBookModal) {
        addBookModal.style.display = "none";
    } else if (editBookModal && event.target == editBookModal) {
        editBookModal.style.display = "none";
    } else if (addPublisherModal && event.target == addPublisherModal) {
        addPublisherModal.style.display = "none";
    } else if (editPublisherModal && event.target == editPublisherModal) {
        editPublisherModal.style.display = "none";
    } else if (addUserModal && event.target == addUserModal) {
        addUserModal.style.display = "none";
    } else if (editUserModal && event.target == editUserModal) {
        editUserModal.style.display = "none";
    } else if (addPenaltyModal && event.target == addPenaltyModal) {
        addPenaltyModal.style.display = "none";
    } else if (addMemberModal && event.target == addMemberModal) {
        addMemberModal.style.display = "none";
    } else if (editMemberModal && event.target == editMemberModal) {
        editMemberModal.style.display = "none";
    } else if (issueBookModal && event.target == issueBookModal) {
        issueBookModal.style.display = "none";
    } else if (emailStudentModal && event.target == emailStudentModal) {
        emailStudentModal.style.display = "none";
    } else if (scanQRModal && event.target == scanQRModal) {
        closeScanQRModal(); // Use function to clear scanner
    } else if (generateReportModal && event.target == generateReportModal) {
        closeGenerateReportModal();
    }
}

function toggleDateInputs(checkbox) {
    const startDate = document.querySelector('input[name="start_date"]');
    const endDate = document.querySelector('input[name="end_date"]');
    
    if (startDate && endDate) {
        if (checkbox.checked) {
            startDate.disabled = true;
            endDate.disabled = true;
        } else {
            startDate.disabled = false;
            endDate.disabled = false;
        }
    }
}