import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from ..forms import PostForm, CommentForm
from ..models import Group, Post, Comment
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test-auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = self.post.author
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create_page_for_authorized_client(self):
        """Валидная форма создает новый пост с изображением."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': PostCreateFormTests.post.text,
            'group': PostCreateFormTests.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.post.author}
        )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                image='posts/small.gif',
            ).exists()
        )

    def test_post_create_page_for_guest_client(self):
        """Валидная форма создает новый пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста от гостя',
            'group': PostCreateFormTests.group.id,
        }
        self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
            ).exists()
        )

    def test_post_edit_page_for_authorized_client(self):
        """Валидная форма редактирует существующий пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': PostCreateFormTests.post.text,
            'group': PostCreateFormTests.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}
        )
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
            ).exists()
        )

    def test_post_edit_page_for_guest_client(self):
        """Валидная форма редактирует существующий пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста от гостя',
            'group': PostCreateFormTests.group.id,
        }
        self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
            ).exists()
        )


class CommentCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.author_client = Client()
        cls.user_author = User.objects.create(username='test-author')
        cls.author_client.force_login(cls.user_author)
        cls.authorized_client = Client()
        cls.user_authorized = User.objects.create(username='test-authorized')
        cls.authorized_client.force_login(cls.user_authorized)
        cls.group = Group.objects.create(
            title='Тестовая группа #2',
            slug='test-slug-com',
            description='Тестовое описание #2',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            group=cls.group,
            text='Тестовый пост для комментария',
        )
        cls.form = CommentForm()

    def test_add_comment_page_for_authorized_client(self):
        """Форма создает новый комментарий авторизованного пользователя."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий к посту'
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
            ).exists()
        )

    def test_add_comment_page_for_guest_client(self):
        """Форма не создает новый комментарий гостя."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий к посту'
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertFalse(
            Comment.objects.filter(
                text=form_data['text'],
            ).exists()
        )

    def test_add_comment_page_for_author_client(self):
        """Форма создает новый комментарий автора поста."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий к посту'
        }
        self.author_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
            ).exists()
        )
