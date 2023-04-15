#include <iostream>
#include <random>
#include <cmath>

using namespace std;

// 生成随机旋转向量
void random_rotation_vector(double &theta, double &phi)
{
    random_device rd;
    mt19937 gen(rd());
    uniform_real_distribution<> dis(0, 2 * M_PI);
    theta = dis(gen);
    phi = dis(gen);
}

// 构建旋转矩阵
void rotation_matrix(double theta, double phi, double R[3][3])
{
    double u[3] = {sin(phi) * cos(theta), sin(phi) * sin(theta), cos(phi)};
    double cos_theta = cos(theta);
    double sin_theta = sin(theta);
    double ux = u[0];
    double uy = u[1];
    double uz = u[2];
    R[0][0] = cos_theta + ux * ux * (1 - cos_theta);
    R[0][1] = ux * uy * (1 - cos_theta) - uz * sin_theta;
    R[0][2] = ux * uz * (1 - cos_theta) + uy * sin_theta;
    R[1][0] = uy * ux * (1 - cos_theta) + uz * sin_theta;
    R[1][1] = cos_theta + uy * uy * (1 - cos_theta);
    R[1][2] = uy * uz * (1 - cos_theta) - ux * sin_theta;
    R[2][0] = uz * ux * (1 - cos_theta) - uy * sin_theta;
    R[2][1] = uz * uy * (1 - cos_theta) + ux * sin_theta;
    R[2][2] = cos_theta + uz * uz * (1 - cos_theta);
}

// 打印矩阵
void print_matrix(double R[3][3])
{
    for (int i = 0; i < 3; i++)
    {
        for (int j = 0; j < 3; j++)
        {
            cout << R[i][j] << ", ";
        }
        cout << endl;
    }
}

bool isOrthogonalMatrix(double matrix[3][3])
{
    // Check if the matrix is a square matrix
    for (int i = 0; i < 3; i++)
    {
        if (sizeof(matrix[i]) / sizeof(matrix[i][0]) != 3)
        {
            return false;
        }
    }

    // Check if the matrix is orthogonal
    for (int i = 0; i < 3; i++)
    {
        for (int j = 0; j < 3; j++)
        {
            double dotProduct = 0;
            for (int k = 0; k < 3; k++)
            {
                dotProduct += matrix[i][k] * matrix[j][k];
            }

            if (i == j)
            {
                if (fabs(dotProduct - 1.0) > 1e-6)
                {
                    return false;
                }
            }
            else
            {
                if (fabs(dotProduct) > 1e-6)
                {
                    return false;
                }
            }
        }
    }

    return true;
}

int main()
{
    double theta, phi;
    random_rotation_vector(theta, phi);
    double R[3][3];
    rotation_matrix(theta, phi, R);
    cout << "Random SO(3) matrix:" << endl;
    print_matrix(R);
    if (isOrthogonalMatrix(R))
    {
        cout << "The matrix is an orthogonal matrix." << endl;
    }
    else
    {
        cout << "The matrix is not an orthogonal matrix." << endl;
    }

    return 0;
}