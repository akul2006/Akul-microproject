// Initialize on load
function checkHash() {
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');
    
    if (tab && document.getElementById(tab)) {
        showPage(tab);
    } else if (window.location.hash) {
        const pageName = window.location.hash.substring(1);
        if (document.getElementById(pageName)) showPage(pageName);
    }
}

document.addEventListener('DOMContentLoaded', checkHash);
// Check immediately in case the script runs after DOMContentLoaded
checkHash();

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
}

// Toggle Notifications
function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    dropdown.classList.toggle('active');
}

// Close notifications when clicking outside
document.addEventListener('click', function (event) {
    const notifIcon = document.querySelector('.notification-icon');
    const dropdown = document.getElementById('notificationDropdown');

    if (!notifIcon.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.classList.remove('active');
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

// Book Modal Functions
function openAddBookModal() {
    document.getElementById('addBookModal').style.display = "block";
}

function closeAddBookModal() {
    document.getElementById('addBookModal').style.display = "none";
}

function openEditBookModal(id, title, authorId, isbn, totalQty, availQty, imageUrl) {
    document.getElementById('editBookId').value = id;
    document.getElementById('editBookTitle').value = title;
    document.getElementById('editBookAuthor').value = authorId;
    document.getElementById('editBookIsbn').value = isbn;
    document.getElementById('editBookTotalQty').value = totalQty;
    document.getElementById('editBookAvailQty').value = availQty;
    document.getElementById('editBookImage').value = imageUrl;
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

// Publisher Modal Functions
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

window.onclick = function (event) {
    const modal = document.getElementById('publisherBooksModal');
    const addAuthorModal = document.getElementById('addAuthorModal');
    const editAuthorModal = document.getElementById('editAuthorModal');
    const authorBioModal = document.getElementById('authorBioModal');
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

    if (event.target == modal) {
        modal.style.display = "none";
    } else if (event.target == addAuthorModal) {
        addAuthorModal.style.display = "none";
    } else if (event.target == editAuthorModal) {
        editAuthorModal.style.display = "none";
    } else if (authorBioModal && event.target == authorBioModal) {
        authorBioModal.style.display = "none";
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
    }
}