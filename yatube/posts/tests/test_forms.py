import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivanov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост 2',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.authorized_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username': 'Ivanov'}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.latest_post = Post.objects.latest('pub_date')
        self.assertEqual(self.latest_post.author.username, 'Ivanov')
        self.assertEqual(self.latest_post.text, 'Тестовый пост 2')
        self.assertEqual(self.latest_post.image, 'posts/small.gif')

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост 3',
            'group': self.group.pk,
        }
        response = self.authorized_author.post(
            reverse('posts:post_edit', kwargs={'post_id': f'{self.post.pk}'}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail',
                    kwargs={'post_id': f'{self.post.pk}'})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.latest_post = Post.objects.latest('pub_date')
        self.assertEqual(self.latest_post.author.username, 'Ivanov')
        self.assertEqual(self.latest_post.text, 'Тестовый пост 3')

    def test_create_comment(self):
        """Валидная форма создает комментарий."""
        comments_count = Comment.objects.filter(post=self.post).count()
        form_data = {
            'text': 'Новый тестовый комментарий',
        }
        response = self.authorized_author.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': f'{self.post.pk}'}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail',
                    kwargs={'post_id': f'{self.post.pk}'}))
        self.assertEqual(Comment.objects.filter(post=self.post).count(),
                         comments_count + 1)
        self.latest_comment = (Comment.objects.filter(post=self.post).
                               latest('created'))
        self.assertEqual(self.latest_comment.author.username, 'Ivanov')
        self.assertEqual(self.latest_comment.text,
                         'Новый тестовый комментарий')
